output "nfs_disk_snapshot_self_link" {
  value = google_compute_snapshot.nfs_snapshot.self_link
}

output "nfs_server_image_self_link" {
  value = google_compute_image.nfs_image.self_link
}

output "mgmt_disk_image_self_link" {
  value = google_compute_image.mgmt_image.self_link
}

output "compute_disk_image_self_link" {
  value = google_compute_image.compute_image.self_link
}