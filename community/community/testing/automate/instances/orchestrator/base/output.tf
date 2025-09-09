
output "bigquery-dataset-id" {
  value = google_bigquery_dataset.orchestrator.dataset_id
}

# Kind of reduntant but okey...
output "bigquery-tables-ids" {
  value = {
    for key, value in google_bigquery_table.orchestrator: key => value.table_id
  }
}

output "orchestrator-sa-email" {
  value = google_service_account.orchestrator.email
}

output "orchestrator-sa-id" {
  value = google_service_account.orchestrator.id
}

output "cluster-name" {
  value = google_container_cluster.orchestrator.name
}

output "cluster-location" {
  value = google_container_cluster.orchestrator.location
}

output "orchestrator-hostname" {
  value = google_compute_instance.orchestrator.hostname
}