resource "google_service_account" "orchestrator" {
  account_id   = "orchestrator-${local.module_suffix}"
  display_name = "Orchestrator Service Account (${local.module_suffix})"
}

resource "google_project_iam_member" "orchestrator" {
  for_each = toset([
    # For using bq
    "roles/bigquery.dataViewer",
    "roles/bigquery.user",
    # For using workload id
    "roles/iam.workloadIdentityUser",
    # For pulling images
    "roles/artifactregistry.reader",
    # For metrics
    "roles/monitoring.viewer",
    "roles/compute.viewer"
  ])

  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.orchestrator.email}"
}

