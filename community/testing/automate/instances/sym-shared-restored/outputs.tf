output "nfs_server_internal_ip" {
  value = module.symphony-shared.nfs_server_internal_ip
}

output "nfs_disk_capacity" {
  value = module.symphony-shared.nfs_disk_capacity
}

output "nfs_disk_mount_point" {
  value = module.symphony-shared.nfs_disk_mount_point
}

output "symphony_mgmt_vms_self_link" {
  value = module.symphony-shared.symphony_mgmt_vms_self_link
}

output "symphony_compute_vms_self_link" {
  value = module.symphony-shared.symphony_compute_vms_self_link
}

output "symphony_mgmt_template_self_link" {
  value = module.symphony-shared.symphony_mgmt_template_self_link
}

output "symphony_compute_template_self_link" {
  value = module.symphony-shared.symphony_compute_template_self_link
}

output "symphony_template_configuration_vars" {
  sensitive = true
  value =  module.symphony-shared.symphony_template_configuration_vars
}