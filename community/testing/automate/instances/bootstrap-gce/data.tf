data "terraform_remote_state" "base_state" {
  backend = "gcs"
  config = {
    bucket = var.state_bucket
    prefix = "base-instances"
  }
}

data "terraform_remote_state" "symphony" {
  backend   = "gcs"
  workspace = var.target_symphony_workspace
  config = {
    bucket = var.state_bucket
    prefix = var.target_symphony_project
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