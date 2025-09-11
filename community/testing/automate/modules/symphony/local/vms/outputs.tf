output "symphony_mgmt_vms_names" {
  value = google_compute_instance_from_template.symphony-mgmt-primary[*].name
}

output "symphony_compute_vms_names" {
  value = google_compute_instance_from_template.symphony-compute[*].name
}

output "symphony_mgmt_vms_self_link" {
  value = google_compute_instance_from_template.symphony-mgmt-primary[*].self_link
}

output "symphony_compute_vms_self_link" {
  value = google_compute_instance_from_template.symphony-compute[*].self_link
}