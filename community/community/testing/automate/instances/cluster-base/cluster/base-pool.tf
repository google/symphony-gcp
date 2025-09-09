resource "google_container_node_pool" "base-pool" {
  name = "base-pool-${local.module_suffix}-${var.cluster_subnet_group_index}"

  cluster = google_container_cluster.test-cluster.name

  # Regional node pool
  location = var.region
  node_locations = local.node_locations

  version = data.google_container_engine_versions.cluster-versions.latest_node_version

  lifecycle {
    ignore_changes = [ version ]
    replace_triggered_by = [ terraform_data.cluster_version_prefix ]
  }

  initial_node_count = var.base_pool_spec.initial_node_count

   # TODO: placement_policy ? 

  autoscaling {
    location_policy = "ANY"
    total_min_node_count = 1
    total_max_node_count = 10
  }

  management {
    auto_repair = true
    auto_upgrade = false
  }

  node_config {
    preemptible  = var.base_pool_spec.preemptible
    spot = var.base_pool_spec.spot
    machine_type = var.base_pool_spec.machine_type

    disk_size_gb = var.base_pool_spec.disk_size
    disk_type    = var.base_pool_spec.disk_type

    # We simply use the node disk
    local_ssd_count = 0
    ephemeral_storage_local_ssd_config {
      local_ssd_count = 0
    }

    image_type = var.image_type

    # Because Symphony supports mostly V1 
    linux_node_config {
      cgroup_mode = "CGROUP_MODE_V1"
    }

    logging_variant = var.base_pool_spec.logging_variant

    # TODO: Add a better service account here...
    # Google recommends custom service accounts that have cloud-platform scope and permissions granted via IAM Roles.
    service_account = data.terraform_remote_state.base_state.outputs.service_account.email
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]

    # taint {
    #   key = "base-pool"
    #   value = "true"
    #   effect = "NO_SCHEDULE"
    # }

    # To allow for the usage of nodeSelector
    labels = {
      "node-pool" = "base-pool"
    }

  }
  # Private cluster
  network_config {
    enable_private_nodes = true
    # Leave default pod range because our subnet support it
  }

  upgrade_settings {
    strategy        = "SURGE"
    max_surge       = 1
    max_unavailable = 1
  }

}