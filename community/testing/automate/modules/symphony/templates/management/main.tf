# Create management VM
resource "google_compute_instance_template" "symphony_mgmt_template" {
  name         = "sym-mgmt-template-${var.module_suffix}"
  project      = var.project_id
  machine_type = var.symphony_mgmt_template.machine_type
  region       = var.region

  disk {
    source_image = var.symphony_mgmt_template.disk.source_image
    disk_type     = var.symphony_mgmt_template.disk.type
    disk_size_gb = var.symphony_mgmt_template.disk.size
    auto_delete  = true
    boot         = true
  }

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

  labels = merge(
    var.common_labels,
    {"resource-type": "sym-mgmt-template"}
  )

  metadata = {
    enable-oslogin = "FALSE"
    ssh-keys       = "${var.configuration_variables.CLUSTERADMIN}:${var.configuration_variables.PUB_KEY}"
  }

  metadata_startup_script = templatefile(local.mgmt_template, {
    common_vars              = var.configuration_variables
    common_functions         = local.common_functions
    common_startup_scripts   = local.common_startup_scripts
    startup_script_functions = local.mgmt_startup_script_functions
    plugin_bootstrap_functions = templatefile(
      "${path.module}/../templates/bootstrap_plugin.tftpl", {
        python_repository                  = var.python_repository
        
        gke_plugin_config                      = file("${path.module}/../scripts/config/gcpgkeinstprov_config.json")
        gke_plugin_template_config             = file("${path.module}/../scripts/config/gcpgkeinstprov_templates.json")
        gke_plugin_template                    = file("${path.module}/../scripts/config/templates/spec-001.yaml")
        gke_provider_script                    = file("${path.module}/../scripts/config/gke_script.sh")
        
        gce_plugin_config                      = file("${path.module}/../scripts/config/gcpgceinstprov_config.json")
        gce_plugin_template_config             = file("${path.module}/../scripts/config/gcpgceinstprov_templates.json")
        gce_provider_script                    = file("${path.module}/../scripts/config/gce_script.sh")

        hostproviders-provider             = file("${path.module}/../scripts/config/hostProviders.provider.json")
        hostproviderplugins-providerplugin = file("${path.module}/../scripts/config/hostProviderPlugins.providerplugin.json")
      }
    )

    environment_variables = {
      EGOCOMPUTEHOST = "N"
    }

    install_only = var.install_only
  })
}

