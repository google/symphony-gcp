output "symphony_mgmt_vms_self_link" {
  value = module.symphony-local.symphony_mgmt_vms_self_link
}

output "symphony_compute_vms_self_link" {
  value = module.symphony-local.symphony_compute_vms_self_link
}

output "symphony_mgmt_template_self_link" {
  value = module.symphony-local.symphony_mgmt_template_self_link
}

output "symphony_compute_template_self_link" {
  value = module.symphony-local.symphony_compute_template_self_link
}

output "symphony_template_configuration_vars" {
  sensitive = true
  value =  module.symphony-local.symphony_template_configuration_vars
}