data "terraform_remote_state" "base_state" {
  backend = "gcs"
  config = {
    bucket = var.state_bucket
    prefix = "base-instances"
  }
}

data "terraform_remote_state" "symphony" {
  backend   = "gcs"
  workspace = var.target_symphony_shared_workspace
  config = {
    bucket = var.state_bucket
    prefix = "sym-shared-restored"
  }
}

data "terraform_remote_state" "orchestrator-base" {
  backend   = "gcs"
  # default bucket...
  config = {
    bucket = var.state_bucket
    prefix = "orchestrator-base"
  }
}

data "terraform_remote_state" "orchestrator-bootstrap" {
  backend   = "gcs"
  # default bucket...
  config = {
    bucket = var.state_bucket
    prefix = "orchestrator-bootstrap"
  }
}

locals {
  log_table_id = data.terraform_remote_state.orchestrator-base.outputs.bigquery-tables-ids["logs-2"]
  log_dataset_id = data.terraform_remote_state.orchestrator-base.outputs.bigquery-dataset-id
}

locals {
  mgmt_vms_map = {
    for idx, value in data.terraform_remote_state.symphony.outputs.symphony_mgmt_vms_self_link : idx => value  
  }
}

data "google_compute_instance" "mgmt_vms" {
  for_each = local.mgmt_vms_map
  self_link = each.value
}

# ========================================== Cluster ==========================================

data "terraform_remote_state" "cluster_output" {
  backend   = "gcs"
  workspace = var.target_cluster_workspace
  config = {
    bucket = var.state_bucket
    prefix = var.bootstrap_from
  }
}

locals {
  cluster_name = data.terraform_remote_state.cluster_output.outputs.cluster_name
  cluster_location = data.terraform_remote_state.cluster_output.outputs.cluster_location
}

data "google_container_cluster" "cluster" {
  name     = local.cluster_name
  location = local.cluster_location
}

locals {
  cluster_data = data.google_container_cluster.cluster
}

