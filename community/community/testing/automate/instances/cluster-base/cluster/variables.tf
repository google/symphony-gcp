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

# ============================== Project ==============================

variable "state_bucket" {
  type        = string
  description = "The terraform state bucket to load data from"
}

# ============================== Cluster ==============================

variable "cluster_version_prefix" {
  type        = string
  description = "The GKE version prefix of the cluster and node pools"
  default     = "1.33."
}

variable "image_type" {
  type        = string
  description = "The image type for the node images. Allowed values are COS_CONTAINERD and UBUNTU_CONTAINERD."
  default     = "COS_CONTAINERD"
}

variable "scaled_control_plane" {
  type        = bool
  description = "Wether or not try to force the creation of a big control-plane"
  default     = true
}

variable "cluster_subnet_group_index" {
  type        = number
  description = "The cluster subnet group to use for the cluster network configuration"
}

variable "auto_provisioning_defaults" {
  type = object({
    disk_type       = string
    disk_size       = number
    logging_variant = string
    management = object({
      auto_repair  = bool
      auto_upgrade = bool
    })
  })
  description = "The node pool configurations to be used by NAP."
}

variable "base_pool_spec" {
  type = object({
    machine_type       = string,
    disk_type          = string,
    disk_size          = number,
    preemptible        = bool,
    spot               = bool,
    initial_node_count = number
    logging_variant    = string
  })
  default = {
    machine_type       = "n2-standard-8"
    disk_size          = 100
    disk_type          = "pd-ssd"
    preemptible        = false
    spot               = false
    initial_node_count = 1
    logging_variant    = "MAX_THROUGHPUT"
  }
  description = "The base pool spec configuration."
}

variable "compute_pools_spec" {
  type = list(
    object({
      name            = string,
      machine_type    = string,
      disk_type       = string,
      disk_size       = number,
      preemptible     = bool,
      spot            = bool,
      logging_variant = string,
      secondary_boot_disks = list(object({
        disk_image = string
        mode       = string
      }))
      management = object({
        auto_repair  = bool
        auto_upgrade = bool
      })
    })
  )
  description = <<EOF
  The compute pool spec configuration. See matrix_sampels/example.json for an example.
  Please note that the order of the node pools spec will impact the automatically created `ComputeClass` on the bootstrap project.
  The order is from higher to lower priority (i.e. node pool spec index 0 => highest priority)
  EOF
}
