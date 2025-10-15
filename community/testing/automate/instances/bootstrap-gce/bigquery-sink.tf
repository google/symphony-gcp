# ===== BigQuery Setup =====

locals {
  observability_dir = "${path.module}/observability"
  sinks_dir = "${local.observability_dir}/sinks"
  transforms_dir = "${local.observability_dir}/transforms"
  pipelines = {
    for fn in fileset(local.sinks_dir, "*.lql.tftpl"): trimsuffix(fn,".lql.tftpl") => {
        "sink": "${local.sinks_dir}/${fn}",
        "transform": "${local.transforms_dir}/${trimsuffix("${fn}",".lql.tftpl")}.js.tftpl"
    }
  }
}

check "pipeline_coherence" {
  assert {
    condition = alltrue(
      concat(
        [for pipeline_name, pipeline in local.pipelines: fileexists(pipeline.sink)],
        [for pipeline_name, pipeline in local.pipelines: fileexists(pipeline.transform)],
      )
    )
    error_message = "The pipeline array is not coherence, please check that all filenames match between schemas, sinks and transforms..."
  }
}

# ===== Pub/Sub Setup =====

resource "google_pubsub_topic" "log_topic" {
  for_each = local.pipelines
  name    = "topic-${each.key}-${local.module_suffix}"

  # Increase message retention for reliability
  message_retention_duration = "604800s" # 7 days (default is 7 days, but explicit is better)

    # Enable message storage policy for better durability
  message_storage_policy {
    allowed_persistence_regions = [var.region] # Specify your region
  }
}

# ===== Logging Sink to Pub/Sub =====

resource "google_logging_project_sink" "bootstrap-sink" {
  for_each = local.pipelines
  project = var.project_id
  name    = "sink-${each.key}-${local.module_suffix}"

  # Destination is the Pub/Sub topic
  destination = "pubsub.googleapis.com/${google_pubsub_topic.log_topic[each.key].id}"

  # Filter for the logs you want to capture
  filter = templatefile(each.value.sink, {
    project_id = var.project_id
  })

  # This creates a unique service account for this sink
  unique_writer_identity = true
}

# 1. Grant the Logging Sink's service account permission to PUBLISH to the topic.
resource "google_pubsub_topic_iam_member" "logging_sink_can_publish" {
  for_each = local.pipelines
  topic   = google_pubsub_topic.log_topic[each.key].name
  role    = "roles/pubsub.publisher"
  member  = google_logging_project_sink.bootstrap-sink[each.key].writer_identity
}

# ===== Dead Letter Queue Setup =====
# This prevents bad messages from blocking the pipeline

# Get the special Google-managed Pub/Sub service account identity.
resource "google_project_service_identity" "pubsub_sa" {
  provider = google-beta
  project  = var.project_id
  service  = "pubsub.googleapis.com"
}

resource "google_pubsub_topic" "dead_letter_topic" {
  for_each = local.pipelines
  name     = "topic-dlq-${each.key}-${local.module_suffix}"
  
  message_retention_duration = "2419200s" # 28 days for investigation
  
  message_storage_policy {
    allowed_persistence_regions = [var.region]
  }
  
}

resource "google_pubsub_subscription" "dead_letter_subscription" {
  for_each = local.pipelines
  name     = "subscription-dlq-${each.key}-${local.module_suffix}"
  topic    = google_pubsub_topic.dead_letter_topic[each.key].name
  
  # Keep DLQ messages longer for debugging
  message_retention_duration = "2419200s" # 28 days
  retain_acked_messages     = true        # Keep for investigation
  
}

resource "google_pubsub_topic_iam_member" "pubsub_can_publish_to_dlq" {
  for_each = local.pipelines
  topic    = google_pubsub_topic.dead_letter_topic[each.key].name
  role     = "roles/pubsub.publisher"
  member   = google_project_service_identity.pubsub_sa.member
}

# ===== Pub/Sub Subscription to BigQuery =====

# 2. Grant the Pub/Sub service account permission to WRITE to the BigQuery Table.
resource "google_bigquery_table_iam_member" "pubsub_can_write_to_bq" {
  for_each = local.pipelines
  dataset_id = local.log_dataset_id
  table_id   = local.log_table_id
  role       = "roles/bigquery.dataEditor"
  member     = google_project_service_identity.pubsub_sa.member
}

resource "google_pubsub_subscription" "log_subscription" {
  for_each = local.pipelines
  project = google_pubsub_topic.log_topic[each.key].project
  name    = "subscription-${each.key}-${local.module_suffix}"
  topic   = google_pubsub_topic.log_topic[each.key].name

  # Enhanced reliability settings
  ack_deadline_seconds       = 600  # 10 minutes for processing
  message_retention_duration = "604800s" # 7 days
  # enable_exactly_once_delivery = false # Not available for BQ

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead_letter_topic[each.key].id
    max_delivery_attempts = 10
  }

  bigquery_config {
    table               = "${var.project_id}.${local.log_dataset_id}.${local.log_table_id}"
    use_table_schema    = true
    drop_unknown_fields = true
  }

  # Your JavaScript UDF for transformations
  message_transforms {
    javascript_udf {
      function_name = "filter"
      code          = templatefile(
        each.value.transform,
        {
          run_id = local.run_id
          project_id = var.project_id
        }
        )
    }
    disabled = false
  }

  # Ensure IAM permissions are created BEFORE the subscription attempts to use them.
  depends_on = [
    google_bigquery_table_iam_member.pubsub_can_write_to_bq,
  ]
}

# Allow the service account to subscribe topics for dead lettering...
resource "google_pubsub_subscription_iam_member" "pubsub_can_subscribe_for_dlq" {
  for_each = local.pipelines
  subscription = google_pubsub_subscription.log_subscription[each.key].name
  role     = "roles/pubsub.subscriber"
  member   = google_project_service_identity.pubsub_sa.member
}

