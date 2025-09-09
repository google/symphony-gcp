output "cluster_name" {
  value = google_container_cluster.test-cluster.name
}

output "cluster_location" {
  value = google_container_cluster.test-cluster.location
}

# For compatibility with cluster-base and creation of CCC.

output "compute_class" {
  value = local.compute_class
}

output "compute_class_node_pools" {
  value = [
    google_container_node_pool.test-pool.name
    ]
}