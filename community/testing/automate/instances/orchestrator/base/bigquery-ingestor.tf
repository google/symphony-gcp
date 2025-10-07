variable "docker_repository" {
  type        = string
  description = "The docker registry server to be used for the BQIngestor images"
}

variable "bigquery_ingestor_image" {
  type        = string
  description = "The name of the BQingestor image and optionally its tag."
  default     = "bqingestor:test"
}

resource "google_cloud_run_service" "bq-ingestor" {
  name     = "bq-ingestor"
  location = var.region

   metadata {
     annotations = {
       "run.googleapis.com/ingress" = "internal-and-cloud-load-balancing"
     }
   }

  template {
    spec {
      containers {
        image = "${var.docker_repository}/${var.bigquery_ingestor_image}"

        ports {
            container_port = 8000
        }

        env {
          name  = "PROJECT_ID"
          value = var.project_id
        }

        env {
          name  = "DATASET_ID"
          value = google_bigquery_dataset.orchestrator.dataset_id
        }

        env {
          name  = "TABLE_ID"
          value = google_bigquery_table.orchestrator["logs"].table_id
        }
      }
      service_account_name = google_service_account.orchestrator.email
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

resource "google_cloud_run_service_iam_member" "egoadmin" {
location = google_cloud_run_service.bq-ingestor.location
  project = google_cloud_run_service.bq-ingestor.project
  service = google_cloud_run_service.bq-ingestor.name
  role = "roles/run.invoker"
  member = data.terraform_remote_state.base_state.outputs.service_account.member
}

output "bq-ingestor-url" {
    value = google_cloud_run_service.bq-ingestor.status[0].url
}