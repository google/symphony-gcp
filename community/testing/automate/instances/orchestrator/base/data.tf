data "terraform_remote_state" "base_state" {
  backend = "gcs"
  config = {
    bucket = var.state_bucket
    prefix = "base-instances"
  }
}

data "terraform_remote_state" "network" {
  count = var.network_from == "cluster-network" ? 1 : 0
  backend   = "gcs"
  config = {
    bucket = var.state_bucket
    prefix = "cluster-network"
  }
}

locals {
  subnet_array = (
    var.network_from == "cluster-network" ? 
    data.terraform_remote_state.network[0].outputs.subnet_array :
    null
  )

  orchestrator_nodes_subnet_data = (
    var.network_from == "cluster-network" ? 
    local.subnet_array[
      data.terraform_remote_state.network[0].outputs.orchestrator_nodes_subnet_index
    ] : null
  )

  orchestrator_vms_subnet_data = (
    var.network_from == "cluster-network" ? 
    local.subnet_array[
      data.terraform_remote_state.network[0].outputs.orchestrator_vm_subnet_index
    ] : null
  )
  
  cluster_orchestrator_subnet = (
    var.network_from == "cluster-network" ? 
    data.terraform_remote_state.network[0].outputs.network.subnets[
      "${local.orchestrator_nodes_subnet_data.subnet_region}/${local.orchestrator_nodes_subnet_data.subnet_name}"
    ] : null
  )

  vm_orchestrator_subnet = (
    var.network_from == "cluster-network" ? 
    data.terraform_remote_state.network[0].outputs.network.subnets[
      "${local.orchestrator_vms_subnet_data.subnet_region}/${local.orchestrator_vms_subnet_data.subnet_name}"
    ] : null
  )

  network = (
    var.network_from == "cluster-network" ? 
    data.terraform_remote_state.network[0].outputs.network.network_self_link :
    data.terraform_remote_state.base_state.outputs.network.network_self_link
  )

  cluster_subnet_self_link = (
    var.network_from == "cluster-network" ? 
    local.cluster_orchestrator_subnet.self_link : data.terraform_remote_state.base_state.outputs.subnet.self_link
  )

  vm_subnet_self_link = (
    var.network_from == "cluster-network" ? 
    local.vm_orchestrator_subnet.self_link : data.terraform_remote_state.base_state.outputs.subnet.self_link
  )

  cluster_master_cidr =(
    var.network_from == "cluster-network" ? 
    data.terraform_remote_state.network[0].outputs.orchestrator_master_ipv4_cidr_block :
    data.terraform_remote_state.base_state.outputs.subnet.ip_cidr_range
  )

  cluster_secondary_range_name = (
    var.network_from == "cluster-network" ? 
    local.cluster_orchestrator_subnet.secondary_ip_range[0].range_name :
    null
  )
  services_secondary_range_name = (
    var.network_from == "cluster-network" ? 
    local.cluster_orchestrator_subnet.secondary_ip_range[1].range_name :
    null
  )
}