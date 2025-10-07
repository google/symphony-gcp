output "cluster_name" {
  value = google_container_cluster.test-cluster.name
}

output "cluster_location" {
  value = google_container_cluster.test-cluster.location
}