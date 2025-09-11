
# For example:
# E2, N4, N2 , N2D, N1, C4 , C3 , C3D, T2D, M1, C2 , C2D, A2

resource "google_container_node_pool" "test-pool" {
  for_each = {for pool in var.compute_pools_spec: pool.name => pool }
  name = "${each.key}-node-pool-${local.module_suffix}-${var.cluster_subnet_group_index}"

  cluster = google_container_cluster.test-cluster.name

  # Regional node pool
  location = var.region
  node_locations = local.node_locations
  version = data.google_container_engine_versions.cluster-versions.latest_node_version

  lifecycle {
    ignore_changes = [ version ]
    replace_triggered_by = [ terraform_data.cluster_version_prefix ]
  }

  initial_node_count = 0

   # TODO: placement_policy ? 

  autoscaling {
    location_policy = "ANY"
    total_min_node_count = 0
    total_max_node_count = 5000
  }

  management {
    auto_repair = each.value.management.auto_repair
    auto_upgrade = each.value.management.auto_upgrade
  }

  node_config {
    preemptible  = each.value.preemptible
    spot = each.value.spot
    machine_type = each.value.machine_type

    # Enable image streaming
    gcfs_config {
      enabled = true
    }

    dynamic secondary_boot_disks {
      for_each = each.value.secondary_boot_disks
      content {
        disk_image = secondary_boot_disks.value.disk_image
        mode = secondary_boot_disks.value.mode
      }
    }

    disk_size_gb = each.value.disk_size
    disk_type    = each.value.disk_type

    # TODO: This might conflict for different machine types
    # The idea is to leave this as it is and use the node storage disk.
    local_ssd_count = 0
    ephemeral_storage_local_ssd_config {
      local_ssd_count = 0
    }

    # Because Symphony supports mostly V1 
    linux_node_config {
      cgroup_mode = "CGROUP_MODE_V1"
    }

    image_type = var.image_type

    logging_variant = each.value.logging_variant

    # TODO: Add a better service account here...
    # Google recommends custom service accounts that have cloud-platform scope and permissions granted via IAM Roles.
    service_account = data.terraform_remote_state.base_state.outputs.service_account.email
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
      # "https://www.googleapis.com/auth/devstorage.read_only",
    ]

    # To allow for the usage of CCC
    labels = {
      "cloud.google.com/compute-class" = local.compute_class
    }

    taint {
      key = "cloud.google.com/compute-class"
      value = local.compute_class
      effect = "NO_SCHEDULE"
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
