# VM
# 	172.${16+cluster_id}.0.0/17 (15 bit address space)
# Nodes
# 	172.${16+cluster_id}.128.0/17 (15 bit address space)
 
# PODs (as large as possible)
# 	10.${cluster_id * 16}.0.0/12 (20 bit address space)
# Services
# 	10.254.${cluster_id * 16}.0/20 (12 bit address space)
 
# master block /28
# 	192.168.${cluster_id}.0/28  (4 bit address space)


locals {
  # Total number of clusters (with orchestrator)
  total_clusters = var.total_cluster_subnet_groups
  # Cluster indexes
  cluster_indexes = range(local.total_clusters) # minus orchestrator
  # Types of subnet
  subnet_types = ["nodes", "vms"]
  # Types of secondary ranges
  secondary_range_types = ["pods", "services"]

  # Cluster subnet groups
  # Each cluster will have associated a GCE and a GKE subnet.
  cluster_subnets_groups = {
    for cluster_index in local.cluster_indexes : cluster_index => {
      for subnet_idx, subnet_type in local.subnet_types : subnet_type => {
        subnet_name           = "cluster-${cluster_index}-${subnet_type}"
        subnet_ip             = (
          subnet_type == "vms" ?
          "172.${16 + cluster_index}.0.0/17" :
          "172.${16 + cluster_index}.128.0/17"
        )
        subnet_region         = var.region
        subnet_private_access = true
      }
    }
  }

  # Subnet array in the format used by the network module...
  cluster_subnet_array = flatten([
    for cluster_idx, cluster_subnets_group in local.cluster_subnets_groups : [
      for subnet_type, subnet_config in cluster_subnets_group : subnet_config
    ]
  ])

  # Auxiliary index map of the format map(cluster_index,subnet_type) => array index
  cluster_subnet_index_map = {
    for cluster_index in local.cluster_indexes : cluster_index => {
      for subnet_idx, subnet_type in local.subnet_types : subnet_type => cluster_index * length(local.subnet_types) + subnet_idx
    }
  }

  # Secondary ranges for GKE (pods and services)
  cluster_secondary_ranges_groups = {
    for cluster_index in local.cluster_indexes : cluster_index => {
      for secondary_idx, secondary_type in local.secondary_range_types : secondary_type => {
        range_name    = "cluster-${cluster_index}-${secondary_type}"
        ip_cidr_range = (
          secondary_type == "pods" ?
          "10.${16 * cluster_index}.0.0/12" :
          "10.254.${16 * cluster_index}.0/20"
        )
      }
    }
  }

  cluster_master_ipv4_cidr_block = {
    for cluster_index in local.cluster_indexes : cluster_index => "192.168.${cluster_index}.0/28"
  }

  # Map secondary ranges to their corresponding node subnets
  cluster_secondary_ranges = {
    for cluster_index in local.cluster_indexes : "cluster-${cluster_index}-nodes" => [
      for secondary_type in local.secondary_range_types : local.cluster_secondary_ranges_groups[cluster_index][secondary_type]
    ]
  }


  # Index = 13 (from 0)
  # Orchestrator subnet to be merged to other subnets
  orchestrator_subnet_array = [
    {
      subnet_name           = "orchestrator-vms"
      subnet_ip             = "172.29.0.0/17"
      subnet_region         = var.region
      subnet_private_access = true
    },
    {
      subnet_name           = "orchestrator-nodes"
      subnet_ip             = "172.29.128.0/17"
      subnet_region         = var.region
      subnet_private_access = true
    },
  ]

  orchestrator_secondary_ranges = {
    orchestrator-nodes = [
      {
        range_name    = "orchestrator-pods"
        ip_cidr_range =  "10.208.0.0/12"
      },
      {
        range_name    = "orchestrator-services"
        ip_cidr_range = "10.254.208.0/20"
      }
    ]
  }

  orchestrator_master_ipv4_cidr_block = "192.168.13.0/28"

  orchestrator_vm_subnet_index        = length(local.cluster_subnet_array)
  orchestrator_nodes_subnet_index     = length(local.cluster_subnet_array) + 1
  orchestrator_secondary_ranges_index = length(local.cluster_secondary_ranges)


  subnet_array = concat(
    local.cluster_subnet_array,
    local.orchestrator_subnet_array
  )

  secondary_ranges = merge(
    local.cluster_secondary_ranges,
    local.orchestrator_secondary_ranges
  )

  all_private_ranges = [
    "10.0.0.0/8",
    "192.168.0.0/16",
    "172.16.0.0/12"
  ]
}
