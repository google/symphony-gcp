output "mgmt_template_self_link_unique" {
  value = google_compute_instance_template.symphony_mgmt_template.self_link_unique
}

output "mgmt_metadata" {
  value = google_compute_instance_template.symphony_mgmt_template.metadata
}

output "mgmt_metadata_startup_script" {
  value = google_compute_instance_template.symphony_mgmt_template.metadata_startup_script
}