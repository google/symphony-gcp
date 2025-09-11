
resource "google_compute_disk" "disk" {
  name     = "nfs-shared-disk-${var.module_suffix}"
  project  = var.project_id
  zone     = var.zone
  snapshot = var.nfs_disk_snapshot_self_link
  type     = var.nfs_server_disk.type
  size     = var.nfs_server_disk.size

  labels = merge(
    var.common_labels,
    {"resource-type": "nfs-server-disk"}
  )
}

locals {
  # This script is symlinked to /automate/common/common.sh
  common_scripts = file("${path.module}/../common.sh")
}

resource "google_compute_instance_template" "nfs_server_template" {
  name         = "nfs-server-template-${var.module_suffix}"
  project      = var.project_id
  machine_type = var.nfs_server_template.machine_type
  region       = var.region

  disk {
    source_image = var.nfs_server_template.disk.source_image
    type         = var.nfs_server_template.disk.type
    disk_size_gb = var.nfs_server_template.disk.size
    auto_delete  = true
    boot         = true
  }

  disk {
    source      = google_compute_disk.disk.name
    auto_delete = var.autodelete_nfs_disk
    boot        = false
  }

  network_interface {
    network_ip = var.ip_address
    subnetwork = var.subnet.self_link
    # Private Network, so no access_config
    # access_config {
    # }
  }

  labels = merge(
    var.common_labels,
    {"resource-type": "nfs-server-template"}
  )

  service_account {
    email  = var.sa_mail
    scopes = ["cloud-platform"]
  }

  metadata = {
    enable-oslogin = "FALSE"
    ssh-keys       = "${var.ssh_user}:${var.public_key}"
  }

  # TODO: Use startup tag as a variable
  metadata_startup_script = <<EOF
      ${local.common_scripts}
      hostnamectl set-hostname symphony-nfs-server-${var.module_suffix}
      dnf install -y nfs-utils
      %{if var.nfs_disk_snapshot_self_link == null}
      lsblk /dev/sdb1 || sgdisk -n 1: /dev/sdb && partprobe
      lsblk -f /dev/sdb1 | grep xfs || mkfs.xfs /dev/sdb1
      %{endif}
      mkdir -p ${var.nfs_mount_point}
      mount -t xfs /dev/sdb1 ${var.nfs_mount_point}
      echo -e '${var.nfs_mount_point}\t${var.subnet.ip_cidr_range}(rw,sync,no_root_squash)' | sudo tee /etc/exports
      %{ for subnet in var.additional_subnets }
      echo -e '${var.nfs_mount_point}\t${subnet}(rw,sync,no_root_squash)' | sudo tee -a /etc/exports
      %{ endfor }
      exportfs -a
      systemctl restart nfs-server
      TAG=startup-done add_compute_self_tag
      EOF

  depends_on = [google_compute_disk.disk]
}

resource "google_compute_instance_from_template" "nfs-server" {
  name    = "nfs-server-${var.module_suffix}"
  project = var.project_id
  zone    = var.zone

  network_interface {
    network_ip = var.ip_address
    subnetwork = var.subnet.self_link
    # Private Network, so no access_config
    # access_config {
    # }
  }

  labels = merge(
    var.common_labels,
    var.cloudops_labels,
    {"resource-type": "nfs-server-node"}
  )

  source_instance_template = google_compute_instance_template.nfs_server_template.self_link_unique

}