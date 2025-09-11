output "mgmt_disk_image_self_link" {
  value = google_compute_image.mgmt_image.self_link
}

output "compute_disk_image_self_link" {
  value = google_compute_image.compute_image.self_link
}