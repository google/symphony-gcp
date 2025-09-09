data "terraform_remote_state" "base_state" {
  backend = "gcs"
  config = {
    bucket = var.state_bucket
    prefix = "base-instances"
  }
}

data "terraform_remote_state" "network" {
  backend = "gcs"
  config = {
    bucket = var.state_bucket
    prefix = "cluster-network"
  }
}

locals {
  network = data.terraform_remote_state.network.outputs.network
  cluster_secondary_ranges_groups = data.terraform_remote_state.network.outputs.cluster_secondary_ranges_groups
  cluster_subnet_index_map = data.terraform_remote_state.network.outputs.cluster_subnet_index_map
  cluster_master_ipv4_cidr_block = data.terraform_remote_state.network.outputs.cluster_master_ipv4_cidr_block
  orchestrator_subnet_array = data.terraform_remote_state.network.outputs.orchestrator_subnet_array
  cluster_subnets_groups = data.terraform_remote_state.network.outputs.cluster_subnets_groups
}