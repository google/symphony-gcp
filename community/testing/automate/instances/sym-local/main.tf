locals {
  module_suffix = terraform.workspace
}

module "symphony-local" {
  source = "../../modules/symphony/local/vms"

  region     = var.region
  zone       = var.zone
  project_id = var.project_id
  public_key = var.public_key

  module_suffix = local.module_suffix

  subnet_ip_cidr_range = local.subnet_ip_cidr_range
  subnet_self_link     = local.subnet_self_link

  service_account_mail = data.terraform_remote_state.base_state.outputs.service_account.email

  install_only = var.install_only

  restore_mgmt_disk = false
  symphony_mgmt_template = var.symphony_mgmt_template
  symphony_mgmt_replicas = var.symphony_mgmt_replicas

  restore_compute_disk = false
  symphony_compute_template = var.symphony_compute_template
  symphony_compute_replicas = var.symphony_compute_replicas

  symphony_vars = var.symphony_vars
  auxiliary_startup_vars = var.auxiliary_startup_vars
  python_repository = var.python_repository

  common_labels = var.common_labels
  cloudops_labels = var.cloudops_labels
}
