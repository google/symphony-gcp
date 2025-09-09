data "terraform_remote_state" "base_state" {
  backend = "gcs"
  config = {
    bucket = var.state_bucket
    prefix = "base-instances"
  }
}

# TODO: Migrate to this https://registry.terraform.io/modules/terraform-google-modules/kubernetes-engine/google/latest
# TODO: Add custom service account with only rights to read artifacts.

data "google_container_engine_versions" "cluster-versions" {
  provider       = google-beta
  location       = var.zone
  version_prefix = "1.31."
  project        = var.project_id
}

resource "google_container_cluster" "test-cluster" {
  name     = "cluster-${local.module_suffix}"
  location = var.zone

  network    = data.terraform_remote_state.base_state.outputs.network.network_self_link
  subnetwork = data.terraform_remote_state.base_state.outputs.subnet.self_link

  # We can't create a cluster with no node pool defined, but we want to only use
  # separately managed node pools. So we create the smallest possible default
  # node pool and immediately delete it.
  remove_default_node_pool = true
  initial_node_count       = 1

  # Private cluster
  private_cluster_config {
    enable_private_nodes = true
    enable_private_endpoint = true
  }

  master_authorized_networks_config {
    cidr_blocks {
      cidr_block = data.terraform_remote_state.base_state.outputs.subnet.ip_cidr_range
      display_name = "Internal subnet"
    }    
  }

  deletion_protection = false

  min_master_version = data.google_container_engine_versions.cluster-versions.latest_master_version

  # TODO: Possibly need to enable this to allow usage of CCC.
  cluster_autoscaling {
    enabled = false

    # resource_limits {
    #   resource_type = "cpu"
    #   maximum       = 4
    # }

    # resource_limits {
    #   resource_type = "memory"
    #   maximum       = 16
    # }

    # auto_provisioning_locations = [ "us-central1-a" ]
  }

  # Workload Identity allows Kubernetes service accounts to act as a user-managed Google IAM Service Account.
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  enterprise_config {
    desired_tier = "STANDARD"
  }

  release_channel {
    channel = "UNSPECIFIED"
  }
}

check "warn" {
  assert {
    condition = (var.project_id == null ? false : false)
    error_message = <<EOF
    WARNING: 
      The current configuration has not been tested!
      google_container_node_pool.test-pool might be misconfigured for usage with CCC at the cluster_autoscaling level.
      In result CCC might not work as expected!

      PS.: Also add ignore changes lifecycle to K8s version on node pool and cluster...
    EOF
  }
}

locals {
  compute_class = "test-pool"
}

resource "google_container_node_pool" "test-pool" {
  name = "node-pool-${local.module_suffix}"

  cluster = google_container_cluster.test-cluster.name

  location       = "us-central1-a"
  node_locations = ["us-central1-a"]
  
  version = data.google_container_engine_versions.cluster-versions.latest_node_version

  initial_node_count = 1

  autoscaling {
    total_min_node_count = 0
    total_max_node_count = 1
    location_policy      = "ANY"
  }

  management {
    auto_upgrade = false
    auto_repair = true
  }

  node_config {
    spot         = false
    preemptible  = false
    machine_type = "e2-medium"

    disk_size_gb = 100
    disk_type    = "pd-standard"

    image_type = "UBUNTU_CONTAINERD"

    # TODO: Add a better service account here...
    # Google recommends custom service accounts that have cloud-platform scope and permissions granted via IAM Roles.
    service_account = data.terraform_remote_state.base_state.outputs.service_account.email
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
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
  }

  upgrade_settings {
    strategy        = "SURGE"
    max_surge       = 1
    max_unavailable = 1
  }
}

resource "google_compute_firewall" "allow_gke_to_gce" {
  name    = "allow-gke-to-gce-${local.module_suffix}"
  network = data.terraform_remote_state.base_state.outputs.network.network_self_link

  allow {
    protocol = "all"
  }

  source_ranges = [google_container_cluster.test-cluster.cluster_ipv4_cidr]
}

