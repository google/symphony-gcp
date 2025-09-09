module "symphony-shared" {
  source = "../../modules/symphony/shared/vms"

  region     = var.region
  zone       = var.zone
  project_id = var.project_id
  service_account_mail = data.terraform_remote_state.base_state.outputs.service_account.email

  module_suffix = local.module_suffix

  common_labels = var.common_labels
  cloudops_labels = var.cloudops_labels

  # =============== Network ===============

  subnet_ip_cidr_range = local.subnet_ip_cidr_range
  subnet_self_link     = local.subnet_self_link

  # =============== Auxiliary Variables ===============

  public_key = var.public_key
  install_only = var.install_only
  symphony_vars = var.symphony_vars
  auxiliary_startup_vars = var.auxiliary_startup_vars

  # =============== Management ===============

  restore_mgmt_disk = false
  symphony_mgmt_template = var.symphony_mgmt_template

  # =============== Compute ===============

  restore_compute_disk = false
  symphony_compute_template = var.symphony_compute_template

  # =============== NFS ===============

  nfs_share = var.nfs_share
  nfs_server_template = var.nfs_server_template
  nfs_disk_snapshot_self_link = var.nfs_disk_snapshot_self_link
  nfs_additional_subnets = local.additional_subnets

  # =============== Plugin ===============

  python_repository = var.python_repository

}

