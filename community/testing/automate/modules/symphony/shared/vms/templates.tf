locals {
  common_vars = merge(
    var.symphony_vars,
    var.auxiliary_startup_vars,
    {
      NFS_IP = "${google_compute_address.nfs_ip.address}"
      NFS_SHARE = "${var.nfs_share}"
      PUB_KEY = "${var.public_key}"
      SHARED_FS_INSTALL = "Y"
    }
  )
}

module "symphony_mgmt_template" {
  source        = "../../templates/management/"
  module_suffix = var.module_suffix

  # Project
  project_id = var.project_id
  region     = var.region

  # Service Account
  service_account_mail = var.service_account_mail

  # Network
  subnet_self_link = var.subnet_self_link

  # Config
  configuration_variables = local.common_vars
  install_only            = var.install_only

  # Templates
  symphony_mgmt_template = var.symphony_mgmt_template

  python_repository = var.python_repository

  # Restore Images
  restore_mgmt_disk = var.restore_mgmt_disk

  common_labels = var.common_labels

  # Access key
  public_key = var.public_key
}

module "symphony_compute_template" {
  source        = "../../templates/compute"
  module_suffix = var.module_suffix

  # Project
  project_id = var.project_id
  region     = var.region

  # Service Account
  service_account_mail = var.service_account_mail

  # Network
  subnet_self_link = var.subnet_self_link

  # Config
  configuration_variables = local.common_vars
  install_only            = var.install_only

  # Templates
  symphony_compute_template = var.symphony_compute_template

  # Restore Images
  restore_compute_disk = var.restore_compute_disk

  common_labels = var.common_labels

  # Access key
  public_key = var.public_key
}