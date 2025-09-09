# ================================================================== BQ ==================================================================

locals {
  bigquery_namespace = "bigquery"
  bigquery_app       = "bigquery-writer"
  bigquery_app_image = "us-docker.pkg.dev/symphony-dev-2/hf-gcp-testing/bqingestor:test"
}

resource "google_bigquery_table" "test" {
  dataset_id = data.terraform_remote_state.orchestrator.outputs.bigquery-dataset-id
  table_id   = "test"
  schema     = <<EOF
    [
        {
            "name": "timestamp",
            "type": "TIMESTAMP",
            "mode": "REQUIRED"
        },
        {
            "name": "data",
            "type": "JSON",
            "mode": "NULLABLE"
        },
        {
            "name": "hostname",
            "type": "STRING",
            "mode": "REQUIRED"
        },
        {
            "name": "direction",
            "type": "STRING",
            "mode": "REQUIRED"
        },
        {
            "name": "script",
            "type": "STRING",
            "mode": "REQUIRED"
        }
    ]
  EOF

  time_partitioning {
    type = "DAY"
  }
  deletion_protection = false
}

resource "google_bigquery_table_iam_member" "test" {
  dataset_id = data.terraform_remote_state.orchestrator.outputs.bigquery-dataset-id
  table_id   = google_bigquery_table.test.table_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${data.terraform_remote_state.orchestrator.outputs.orchestrator-sa-email}"
}

# ================================================================== K8s ==================================================================

# Create the bigquery namespace
resource "kubernetes_namespace" "bigquery" {
  metadata {
    name = local.bigquery_namespace
  }
}

# Create the service account
resource "kubernetes_service_account" "bigquery_writer" {
  metadata {
    name      = local.bigquery_app
    namespace = kubernetes_namespace.bigquery.metadata[0].name
    annotations = {
      "iam.gke.io/gcp-service-account" = "${data.terraform_remote_state.orchestrator.outputs.orchestrator-sa-email}"
    }
  }
}

resource "kubernetes_deployment" "bigquery_writer" {
  metadata {
    name      = local.bigquery_app
    namespace = kubernetes_namespace.bigquery.metadata[0].name
    labels = {
      app = local.bigquery_app
    }
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = local.bigquery_app
      }
    }

    template {
      metadata {
        labels = {
          app = local.bigquery_app
        }
      }

      spec {
        service_account_name = kubernetes_service_account.bigquery_writer.metadata[0].name

        container {
          image             = local.bigquery_app_image
          image_pull_policy = "Always"
          name              = local.bigquery_app

          env {
            name  = "PROJECT_ID"
            value = var.project_id
          }

          env {
            name  = "DATASET_ID"
            value = data.terraform_remote_state.orchestrator.outputs.bigquery-dataset-id
          }

          env {
            name  = "TABLE_ID"
            value = data.terraform_remote_state.orchestrator.outputs.bigquery-tables-ids["logs-2"]
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "bq_ilb_svc" {
  metadata {
    name = local.bigquery_app
    namespace = kubernetes_namespace.bigquery.metadata[0].name
    annotations = {
      "networking.gke.io/load-balancer-type" = "Internal"
    }
  }

  lifecycle {
    ignore_changes = [ metadata[0].annotations ]
  }

  spec {
    type                     = "LoadBalancer"
    external_traffic_policy  = "Cluster"
    
    selector = {
      app = local.bigquery_app
    }
    
    port {
      name        = "tcp-port"
      protocol    = "TCP"
      port        = 80
      target_port = 8000
    }
  }
}

output "bg_svc_ip" {
  value = kubernetes_service.bq_ilb_svc.status[0].load_balancer[0].ingress[0].ip
  description = "Internal IP address of the load balancer"
}

output "bq_table_id" {
  value = google_bigquery_table.test.table_id
}

output "bq_dataset_id" {
  value = data.terraform_remote_state.orchestrator.outputs.bigquery-dataset-id
}

# TODO
# output "bq_pod_ip" {
# }