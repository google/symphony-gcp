output "nfs_disk_id" {
  value = google_compute_disk.disk.id
}

output "nfs_server_name" {
  value = google_compute_instance_from_template.nfs-server.name
}

output "nfs_server_self_link" {
  value = google_compute_instance_from_template.nfs-server.self_link
}

output "nfs_disk_mount_point" {
  value = var.nfs_mount_point
}

output "nfs_disk_capacity" {
  value = var.nfs_server_disk.size
}

output "nfs_server_internal_ip" {
  value = google_compute_instance_from_template.nfs-server.network_interface.0.network_ip
}


