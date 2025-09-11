# =========================== Service Account ===========================

# # Create a service account for GCP operations
resource "google_service_account" "egoadmin-sa" {
  account_id   = "egoadmin"
  display_name = "Symphony Service Account"
}

# Grant necessary permissions to the service account
resource "google_project_iam_member" "egoadmin-sa-roles" {
  for_each = toset([
    "roles/logging.logWriter",
    "roles/compute.viewer",
    "roles/compute.instanceAdmin.v1",
    "roles/compute.networkUser",
    "roles/compute.imageUser",
    "roles/monitoring.metricWriter",
    "roles/storage.objectViewer",
    "roles/container.developer",
    "roles/compute.storageAdmin",
    "roles/artifactregistry.reader", # For reading the artifact registry
    "roles/container.defaultNodeServiceAccount" # For using as node pool svc account
    # For impersonation through IAP.
    # "roles/iap.httpsResourceAccessor",
    # "roles/iap.tunnelResourceAccessor",
    # "roles/compute.osLogin",
    # "roles/compute.osAdminLogin",
    # "roles/iam.serviceAccountUser"
  ])

  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.egoadmin-sa.email}"
}


# =========================== Default Compute SA ===========================


data "google_compute_default_service_account" "default" {
}

# Grant necessary permissions to the service account
resource "google_project_iam_member" "default" {
  for_each = toset([
    "roles/artifactregistry.reader", # For reading the artifact registry
    "roles/container.defaultNodeServiceAccount", # For being a node service account
    "roles/compute.admin", # For using cloudbuild
    "roles/compute.serviceAgent", # For using cloudbuilds
    "roles/storage.objectCreator", # For using cloudbuilds
    "roles/storage.objectViewer", # For using cloudbuilds
  ])

  project = var.project_id
  role = each.key
  member = "serviceAccount:${data.google_compute_default_service_account.default.email}"
}

# REF: For building secondary boot images / using cloud build
# https://github.com/ai-on-gke/tools/tree/main/gke-disk-image-builder#cloud-build