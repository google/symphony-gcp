# Create management VM
resource "google_compute_instance_template" "symphony_compute_template" {
  name         = "sym-compute-template-${var.module_suffix}"
  project      = var.project_id
  machine_type = var.symphony_compute_template.machine_type
  region       = var.region

  disk {
    source_image = var.symphony_compute_template.disk.source_image
    disk_type    = var.symphony_compute_template.disk.type
    disk_size_gb = var.symphony_compute_template.disk.size
    auto_delete  = true
    boot         = true
  }

  labels = merge(
    var.common_labels,
    {"resource-type": "sym-compute-template"}
  )

  service_account {
    email  = var.service_account_mail
    scopes = ["cloud-platform"]
  }

  network_interface {
    subnetwork = var.subnet_self_link
    # Private Network, so no access_config
    # access_config {
    #   // Ephemeral IP
    # }
  }

  metadata = {
    enable-oslogin = "FALSE"
    ssh-keys       = "${var.configuration_variables.CLUSTERADMIN}:${var.configuration_variables.PUB_KEY}"
  }

  metadata_startup_script = templatefile(local.compute_template, {
    common_vars              = var.configuration_variables
    common_functions         = local.common_functions
    common_startup_scripts   = local.common_startup_scripts
    startup_script_functions = local.compute_startup_script_functions

    environment_variables = {
      EGOCOMPUTEHOST = "Y"
    }

    install_only = var.install_only
  })
}
