# ============================== Project ==============================

variable "project_id" {
  type        = string
  description = "The GCP project ID"
}

variable "region" {
  type        = string
  description = "The GCP project region"
}

variable "zone" {
  type        = string
  description = "The GCP project zone"
}

variable "state_bucket" {
  type        = string
  description = "The terraform state bucket to load data from"
}

# ============================== Network ==============================

variable "total_cluster_subnet_groups" {
  type = number
  description = <<EOF
  This value can be up to 10 (possibly streched to 12 but needs confirmation...)
  The number of clusters subnet groups to generate, which correspond to the following subnets:
    - Nodes 
    - VMs (Symphony clyster)
    - Pods
    - Services
    - Master Nodes

  Additionally, this also generates the Orchestrator subnets which are not accounted for in this variable:
    - Nodes
    - VMs 
    - Pods
    - Services
    - Master Nodes
  EOF

  validation {
    condition = var.total_cluster_subnet_groups <= 10
    error_message = "Only up to 10 subnet groups are allowed"
  }
}