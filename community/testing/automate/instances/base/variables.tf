variable "module_suffix" {
  type        = string
  description = "The suffix to be appended to the resources created by this module"
}

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

# ============================== Network ==============================

variable "subnet_ip_cidr_range" {
  type        = string
  description = "The subnet ip CIDR range to be used by the NFS and cluster."
}

# ============================== Auth ==============================

variable "private_key" {
  type = string
  description = "Private key to be used for general maintenance"
  sensitive = true
}


