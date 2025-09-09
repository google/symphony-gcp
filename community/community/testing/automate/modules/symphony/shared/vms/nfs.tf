
resource "google_compute_address" "nfs_ip" {
  name         = "nfs-ip-${var.module_suffix}"
  project      = var.project_id
  region       = var.region
  subnetwork   = var.subnet_self_link
  address_type = "INTERNAL"

  labels = merge(
    var.common_labels,
    {"resource-type": "nfs-server-ip"}
  )
}

module "nfs_server" {
  source = "../../nfs-server/vm"

  nfs_mount_point             = var.nfs_share
  nfs_disk_snapshot_self_link = var.nfs_disk_snapshot_self_link

  project_id = var.project_id
  region     = var.region
  zone       = var.zone

  sa_mail = var.service_account_mail
  subnet = {
    self_link     = var.subnet_self_link
    ip_cidr_range = var.subnet_ip_cidr_range
  }
  ip_address = google_compute_address.nfs_ip.address
  additional_subnets = var.nfs_additional_subnets

  module_suffix = var.module_suffix

  nfs_server_template = var.nfs_server_template
  nfs_server_disk = var.nfs_server_disk

  common_labels = var.common_labels
  cloudops_labels = var.cloudops_labels

  # Access key
  public_key = var.public_key
  ssh_user   = local.common_vars.CLUSTERADMIN
}
