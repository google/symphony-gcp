# TODO...

# cluster subnets (array)
# cluster index
# cluster name array
# cluster location array

# output "cluster_subnets" {
#     value = local.cluster_subnets_groups
# }

output "network" {
    value = module.network
}

output "subnet_array" {
    value = local.subnet_array
}

output "cluster_secondary_ranges_groups" {
    value = local.cluster_secondary_ranges_groups
}

output "cluster_subnet_index_map" {
    value = local.cluster_subnet_index_map
}

output "cluster_master_ipv4_cidr_block" {
    value = local.cluster_master_ipv4_cidr_block
}

output "cluster_subnets_groups" {
    value = local.cluster_subnets_groups
}

output "orchestrator_vm_subnet_index" {
   value = local.orchestrator_vm_subnet_index
}

output "orchestrator_nodes_subnet_index" {
   value = local.orchestrator_nodes_subnet_index
}

output "orchestrator_master_ipv4_cidr_block" {
  value = local.orchestrator_master_ipv4_cidr_block
}

output "orchestrator_subnet_array" {
    value = local.orchestrator_subnet_array
}