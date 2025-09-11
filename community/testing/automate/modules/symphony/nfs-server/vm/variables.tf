variable "module_suffix" {
  type        = string
  description = "The suffix to be appended to the resources created by this module"
}

# ============================== Project ==============================

variable "project_id" {
  type        = string
  description = "Project to deploy the instance and template"
}

variable "region" {
  type        = string
  description = "Region to deploy the instance and template"
}

variable "zone" {
  type        = string
  description = "The zone to deploy the NFS server instance"
}

# ============================== Service Account ==============================

variable "sa_mail" {
  type        = string
  description = "Service Account email for the creation of the NFS server instance"
}

# ============================== Network ==============================

variable "subnet" {
  type = object({
    ip_cidr_range = string
    self_link     = string
  })
  description = "The subnet of the NFS server"
}

variable "additional_subnets" {
  type = list(string)
  description = "Additional subnets to export for the NFS server"
  default = []
}

variable "ip_address" {
  type        = string
  description = "The IP address of the NFS server"
}

# ============================== Disk ==============================

variable "nfs_disk_snapshot_self_link" {
  type        = string
  description = "The link to the snapshot to be restored on to the NFS disk."
  default     = null
}

variable "autodelete_nfs_disk" {
  type        = bool
  description = "Whether to enable NFS disk autodeletion."
  default     = false
}

variable "nfs_server_disk" {
  type = object({
    type = string
    size = number
  })
  description = "The specification of the shared NFS disk"
  default = {
    type = "pd-standard"
    size = 200
  }
}

# ============================== Server ==============================

variable "nfs_mount_point" {
  type    = string
  default = "/mnt/nfs-disk"
}

variable "nfs_server_template" {
  type = object({
    machine_type = string
    disk = object({
      source_image = string
      type         = string
      size         = number
    })
  })
  description = "The specification of the NFS server"
  default = {
    machine_type = "n2-standard-2"
    disk = {
      source_image = "rhel-cloud/rhel-8"
      type         = "pd-standard"
      size         = 30
    }
  }
}

# ============================== Labels ============================== 

variable "common_labels" {
  type = any
  description = "The labels to be applied to the machines of tqcdis module. Needs to be an object."
  default = { 
    test-id = "manual-dev"
  }
}

variable "cloudops_labels" {
  type = any
  description = "The cloudops policy label for installing the cloudops agent."
  default = {
    goog-ops-agent-policy = "enabled"
  }
}

# ============================== Other ==============================

variable "restore_boot_disk" {
  type    = bool
  default = false
}

# ============================== Access ==============================

variable "ssh_user" {
  type        = string
  description = "The user to be associated to the SSH key."
  sensitive   = true
}

variable "public_key" {
  type        = string
  description = "The public SSH key to be used for access."
  sensitive   = true
}