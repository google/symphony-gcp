data "google_compute_default_service_account" "default" {
}

resource "google_service_account_iam_binding" "orchestrator-workload-identity" {
  service_account_id = data.terraform_remote_state.orchestrator.outputs.orchestrator-sa-id
  role               = "roles/iam.workloadIdentityUser"
  members = [
    "serviceAccount:${var.project_id}.svc.id.goog[${local.bigquery_namespace}/${local.bigquery_app}]",
    "serviceAccount:${var.project_id}.svc.id.goog[${local.grafana_namespace}/${local.grafana_app}]",
  ]
}

