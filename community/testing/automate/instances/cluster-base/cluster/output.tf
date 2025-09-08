output "cluster_name" {
  value = google_container_cluster.test-cluster.name
}

output "cluster_location" {
  value = google_container_cluster.test-cluster.location
}

output "compute_class" {
  value = local.compute_class
}

output "compute_class_node_pools" {
  value = [
    for pool in var.compute_pools_spec: 
    google_container_node_pool.test-pool[pool.name].name
    ]
}