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
  subnet_ip_cidr_range = (
    var.network_from == "cluster-network" ? 
      data.terraform_remote_state.network[0].outputs.cluster_subnets_groups[tostring(var.cluster_index)].vms.subnet_ip :
      data.terraform_remote_state.base_state.outputs.subnet.ip_cidr_range
  )
  subnet_self_link = (
    var.network_from == "cluster-network" ? 
      data.terraform_remote_state.network[0].outputs.network.subnets_self_links[
        data.terraform_remote_state.network[0].outputs.cluster_subnet_index_map[tostring(var.cluster_index)].vms
      ] :
      data.terraform_remote_state.base_state.outputs.subnet.self_link
  )
  additional_subnets = ( # For exporting the NFS server
    var.network_from == "cluster-network" ?
      [ data.terraform_remote_state.network[0].outputs.cluster_subnets_groups[tostring(var.cluster_index)].nodes.subnet_ip, # nodes
        data.terraform_remote_state.network[0].outputs.cluster_secondary_ranges_groups[tostring(var.cluster_index)].pods.ip_cidr_range, # pods
        data.terraform_remote_state.network[0].outputs.cluster_secondary_ranges_groups[tostring(var.cluster_index)].services.ip_cidr_range # services
      ] : [] # No additional for standard deployment 
  )
}
