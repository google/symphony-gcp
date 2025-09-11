module "symphony-shared" {
  source = "../../modules/symphony/shared/vms"

  region               = var.region
  zone                 = var.zone
  project_id           = var.project_id
  service_account_mail = data.terraform_remote_state.base_state.outputs.service_account.email

  module_suffix = local.module_suffix

  common_labels = var.common_labels
  cloudops_labels = var.cloudops_labels

  # =============== Network ===============

  subnet_ip_cidr_range = local.subnet_ip_cidr_range
  subnet_self_link     = local.subnet_self_link

  # =============== Auxiliary Variables ===============

  public_key = var.public_key
  symphony_vars = var.symphony_vars
  auxiliary_startup_vars = var.auxiliary_startup_vars
  install_only = false

  # =============== NFS ===============

  nfs_disk_snapshot_self_link = data.terraform_remote_state.ci-images.outputs.nfs_disk_snapshot_self_link
  nfs_server_template = {
    machine_type = var.nfs_server_template.machine_type
    disk = {
      source_image = data.terraform_remote_state.ci-images.outputs.nfs_server_image_self_link
      type         = var.nfs_server_template.disk.type
      size         = var.nfs_server_template.disk.size
    }
  }
  nfs_server_disk = var.nfs_server_disk
  nfs_additional_subnets = local.additional_subnets
  
  # =============== Compute ===============

  restore_compute_disk = true
  symphony_compute_template = {
    machine_type = var.symphony_mgmt_template.machine_type
    disk = {
      source_image = data.terraform_remote_state.ci-images.outputs.compute_disk_image_self_link
      type         = var.symphony_mgmt_template.disk.type
      size         = var.symphony_mgmt_template.disk.size
    }
  }

  symphony_compute_replicas = var.symphony_compute_replicas

  # =============== Management ===============

  restore_mgmt_disk = true
  symphony_mgmt_template = {
    machine_type = var.symphony_compute_template.machine_type
    disk = {
      source_image = data.terraform_remote_state.ci-images.outputs.mgmt_disk_image_self_link
      type         = var.symphony_compute_template.disk.type
      size         = var.symphony_compute_template.disk.size
    }
  }

  symphony_mgmt_replicas = var.symphony_mgmt_replicas

  # =============== Plugin ===============

  python_repository = var.python_repository

}
