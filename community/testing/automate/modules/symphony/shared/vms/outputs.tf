output "symphony_mgmt_vms_names" {
  value = google_compute_instance_from_template.symphony-mgmt[*].name
}

output "symphony_compute_vms_names" {
  value = google_compute_instance_from_template.symphony-compute[*].name
}

output "symphony_mgmt_vms_self_link" {
  value = google_compute_instance_from_template.symphony-mgmt[*].self_link
}

output "symphony_compute_vms_self_link" {
  value = google_compute_instance_from_template.symphony-compute[*].self_link
}

output "symphony_compute_template_self_link" {
  value = module.symphony_compute_template.compute_template_self_link_unique
}

output "symphony_mgmt_template_self_link" {
  value = module.symphony_mgmt_template.mgmt_template_self_link_unique
}

output "nfs_disk_id" {
  value = module.nfs_server.nfs_disk_id
}

output "nfs_server_name" {
  value = module.nfs_server.nfs_server_name
}

output "nfs_server_self_link" {
  value = module.nfs_server.nfs_server_self_link
}

output "nfs_server_internal_ip" {
  value = module.nfs_server.nfs_server_internal_ip
}

output "nfs_disk_capacity" {
  value = module.nfs_server.nfs_disk_capacity
}

output "nfs_disk_mount_point" {
  value = module.nfs_server.nfs_disk_mount_point
}
