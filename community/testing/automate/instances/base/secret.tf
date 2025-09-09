# Create the secret
resource "google_secret_manager_secret" "private_key_secret" {
  secret_id = "egoadmin_private_key"
  project   = var.project_id

  replication {
    auto {}
  }

}

resource "google_secret_manager_secret_version" "private_key_version" {
  secret      = google_secret_manager_secret.private_key_secret.id
  secret_data = var.private_key
}

# IAM binding to allow specific service account to access the secret
resource "google_secret_manager_secret_iam_binding" "secret_accessor" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.private_key_secret.secret_id
  role      = "roles/secretmanager.secretAccessor"

  members = [
    "serviceAccount:${google_service_account.egoadmin-sa.email}",
    "user:casey.lineberry@accenture.com"
  ]
}

output "private_key_secret_name" {
  description = "Name of the created private key secret"
  value       = google_secret_manager_secret.private_key_secret.secret_id
}