locals {
  plugin_pubsub_topic = "hf-gce-vm-events"
}

resource "google_pubsub_topic" "plugin-pubsub" {
    name = local.plugin_pubsub_topic
}

resource "google_logging_project_sink" "plugin-sink" {
    project = var.project_id
    name = "${local.plugin_pubsub_topic}-sink"
    description = "Exports MIG VM create/delete audit logs to Pub/Sub"

    destination = "pubsub.googleapis.com/${google_pubsub_topic.plugin-pubsub.id}"

    filter = <<EOF
    logName="projects/${var.project_id}/logs/cloudaudit.googleapis.com%2Factivity"
    resource.type=("gce_instance_group_manager" OR "gce_instance")
    protoPayload.methodName=(
      "v1.compute.instanceGroupManagers.createInstances"
      OR
      "v1.compute.instanceGroupManagers.deleteInstances"
      OR
      "v1.compute.instances.delete"
    )
    EOF
}

resource "google_pubsub_topic_iam_member" "plugin-sink-can-publish" {
  topic   = google_pubsub_topic.plugin-pubsub.name
  role    = "roles/pubsub.publisher"
  member  = google_logging_project_sink.plugin-sink.writer_identity
}

resource "google_pubsub_subscription" "plugin-pubsub-subscription" {
    name = "${local.plugin_pubsub_topic}-sub"
    topic = google_pubsub_topic.plugin-pubsub.name
}

resource "google_pubsub_subscription_iam_member" "egoadmin-can-subscribe" {
    subscription = google_pubsub_subscription.plugin-pubsub-subscription.name
    role = "roles/pubsub.subscriber"
    member = data.terraform_remote_state.base_state.outputs.service_account.member
}