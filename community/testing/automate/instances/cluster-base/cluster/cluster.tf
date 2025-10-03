data "google_container_engine_versions" "cluster-versions" {
  provider       = google-beta
  location       = var.zone
  version_prefix = var.cluster_version_prefix
  project        = var.project_id
}

resource "terraform_data" "cluster_version_prefix" {
  input = var.cluster_version_prefix
}

resource "google_container_cluster" "test-cluster" {
  name = "cluster-${local.module_suffix}-${var.cluster_subnet_group_index}"
  # Regional cluster
  location            = var.region
  deletion_protection = false
  project             = var.project_id

  # ======================= Version =======================

  min_master_version = data.google_container_engine_versions.cluster-versions.latest_master_version
  release_channel {
    channel = "UNSPECIFIED"
  }

  lifecycle {
    ignore_changes = [
      # Ignore changes to minimal accepted version...
      min_master_version,
      # Ignore default node pool config changes since its deleted...
      node_config 
    ]
    replace_triggered_by = [ terraform_data.cluster_version_prefix ]
  }

  maintenance_policy {
    recurring_window {
      recurrence = "FREQ=WEEKLY;BYDAY=SA,SU"
      start_time = "2019-01-01T00:00:00Z"
      end_time = "2019-01-02T00:00:00Z"
    }
  }

  # ======================= Control Plane =======================

  # This ensures a large control plane.
  remove_default_node_pool = true
  initial_node_count       = var.scaled_control_plane ? 500 : 1

  # Sets the initial node config
  # Use a small value for this in order to avoid reaching quotas...
  node_config {
    disk_size_gb = var.auto_provisioning_defaults.disk_size
    disk_type = var.auto_provisioning_defaults.disk_type
  }

  # ======================= Node Pool =======================

  # UNUSED because this relates only to default-node-pool
  # node_config {}

  # UNUSED because this implies "only pools associated w/ cluster" -> blocks node pool (de)attach.
  # node_pool {}

  # Settings applied by default to node pools if not overwriten
  node_pool_defaults {

    node_config_defaults {

      # This option uses the fluentbit maxthroughput daemonset, 
      # which creates the following containers:
      # `fluentbit` (1 vCPU), `fluentbit-gke` (1 vCPU), `fluentbit-metric-collector` (5m vCPU) 
      # which is quite a lot for small machines...
      logging_variant = var.auto_provisioning_defaults.logging_variant

      # Enable Google Container Filesystem (GCPS) 
      # This allows for image streaming, which decreases scaleup time
      gcfs_config {
        enabled = true
      }


    }
  }

  # ======================= Network =======================

  # We do this in order to reduce the address space used 
  # by pods on each node to 32, instead of 256 (110). 
  default_max_pods_per_node = 32

  network = local.network.network_self_link
  subnetwork = local.network.subnets_self_links[
    local.cluster_subnet_index_map[var.cluster_subnet_group_index]["nodes"]
  ]

  networking_mode   = "VPC_NATIVE"
  datapath_provider = "ADVANCED_DATAPATH"

  # Private cluster
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = true
    master_ipv4_cidr_block  = local.cluster_master_ipv4_cidr_block[var.cluster_subnet_group_index]
  }

  # Subnets automatically managed by GKE
  ip_allocation_policy {
    stack_type                    = "IPV4"
    cluster_secondary_range_name  = local.cluster_secondary_ranges_groups[tostring(var.cluster_subnet_group_index)].pods.range_name
    services_secondary_range_name = local.cluster_secondary_ranges_groups[tostring(var.cluster_subnet_group_index)].services.range_name
  }

  master_authorized_networks_config {

    # Allow access from orchestrator subnets
    dynamic "cidr_blocks" {
      for_each = local.orchestrator_subnet_array
      content {
        cidr_block   = cidr_blocks.value.subnet_ip
        display_name = cidr_blocks.value.subnet_name
      }
    }

    # Allow access from this cluster's VM subnet
    cidr_blocks {
      cidr_block   = local.cluster_subnets_groups[var.cluster_subnet_group_index]["vms"].subnet_ip
      display_name = local.cluster_subnets_groups[var.cluster_subnet_group_index]["vms"].subnet_name
    }

    # Allow access from this cluster's nodes subnet (for kubectl from nodes)
    cidr_blocks {
      cidr_block   = local.cluster_subnets_groups[var.cluster_subnet_group_index]["nodes"].subnet_ip
      display_name = local.cluster_subnets_groups[var.cluster_subnet_group_index]["nodes"].subnet_name
    }

    # Disable GKE access from VMs public IPs
    gcp_public_cidrs_access_enabled = false
  }

  # dns_config {
  #   cluster_dns       = "CLOUD_DNS"
  #   cluster_dns_scope = "VPC_SCOPE" # Let the cluster access the VMs...
  #   cluster_dns_domain = "symphony.local"
  # }

  # ======================= Autoscaling =======================

  # In theory this should not be used if we configured correctly our CCC
  # and workloads to not autoscale by using node-pools...
  cluster_autoscaling {
    enabled             = true
    autoscaling_profile = "OPTIMIZE_UTILIZATION"
    # These limits are actually global to the cluster
    # and not limited to autoscaling
    resource_limits {
      resource_type = "cpu"
      minimum       = 1
      maximum       = 150000 # Let's leave some margin for our 100k target.
    }
    resource_limits {
      resource_type = "memory"
      minimum       = 1
      maximum       = 2400000 # Lets use 16x1 ratio for a high margin.
    }
    auto_provisioning_defaults {
      # Enable auto repair, block auto upgrades
      management {
        auto_repair  = true
        auto_upgrade = false
      }

      upgrade_settings {
        strategy        = "SURGE"
        max_surge       = 1
        max_unavailable = 1
      }

      disk_size = var.auto_provisioning_defaults.disk_size
      disk_type = var.auto_provisioning_defaults.disk_type

      image_type = var.image_type

      # TODO: Add a better service account here...
      # Google recommends custom service accounts that have cloud-platform scope and permissions granted via IAM Roles.
      service_account = data.terraform_remote_state.base_state.outputs.service_account.email
      oauth_scopes = [
        "https://www.googleapis.com/auth/cloud-platform",
        "https://www.googleapis.com/auth/devstorage.read_only" # Required for image type UBUNTU_CONTAINERD.
      ]

      # Not needed... yet
      # shielded_instance_config {}
    }
  }

  # ======================= Traceability =======================

  monitoring_config {
    # advanced_datapath_observability_config {
    #   enable_metrics = true
    #   enable_relay   = false
    # }

    enable_components = [
      "SYSTEM_COMPONENTS",
      "APISERVER",
      "SCHEDULER",
      "CONTROLLER_MANAGER",
      "STORAGE",
      "HPA",
      "POD",
      "DAEMONSET",
      "DEPLOYMENT",
      "STATEFULSET",
      "CADVISOR",
      "KUBELET",
      # DCGM
      # JOBSET
    ]
    managed_prometheus {
      enabled = true
    }
  }

  logging_config {
    enable_components = [
      "SYSTEM_COMPONENTS",
      "APISERVER",
      "CONTROLLER_MANAGER",
      "SCHEDULER",
      "WORKLOADS"
    ]
  }

  # ======================= Addons =======================

  addons_config {
    # gcp_filestore_csi_driver_config {
    #   enabled = true # Enable filestore to use as DNS for mounting
    # }
    gce_persistent_disk_csi_driver_config {
      enabled = true
    }
    dns_cache_config {
      enabled = true
    }
  }

  # ======================= Other =======================

  # Workload Identity allows Kubernetes service accounts to act as a user-managed Google IAM Service Account.
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  enterprise_config {
    desired_tier = "STANDARD"
  }

}
