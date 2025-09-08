

resource "google_container_cluster" "orchestrator" {
  name             = "orchestrator-${local.module_suffix}"
  location         = var.region
  enable_autopilot = true

  network    = local.network
  subnetwork = local.cluster_subnet_self_link

  # Private cluster
  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = true
    master_ipv4_cidr_block = local.cluster_master_cidr
  }

  master_authorized_networks_config {

    # Allow access from everywhere subnets
    dynamic "cidr_blocks" {
      for_each = local.subnet_array
      content {
        cidr_block   = cidr_blocks.value.subnet_ip
        display_name = cidr_blocks.value.subnet_name
      }
    }
    
  }

  dynamic ip_allocation_policy {
    for_each = var.network_from == "cluster-network" ? [1] : []
    content {
      stack_type                    = "IPV4"
      cluster_secondary_range_name  = local.cluster_secondary_range_name
      services_secondary_range_name = local.services_secondary_range_name
    }
  }

  enable_l4_ilb_subsetting = true

  deletion_protection = false
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  enterprise_config {
    desired_tier = "STANDARD"
  }

  # Note: node_config is not supported/needed for Autopilot clusters
  # Autopilot manages nodes automatically including service accounts
  # If you need custom service accounts, use workload identity instead
}

resource "google_compute_firewall" "allow_gke_to_gce" {
  count = var.network_from == "cluster-network" ? 0 : 1
  name    = "allow-gke-orchestrator-to-gce-${local.module_suffix}"
  network = data.terraform_remote_state.base_state.outputs.network.network_self_link

  allow {
    protocol = "all"
  }

  source_ranges = [
    google_container_cluster.orchestrator.cluster_ipv4_cidr,
    google_container_cluster.orchestrator.services_ipv4_cidr
    ]
}


