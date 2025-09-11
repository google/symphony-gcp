# ======================== Google Settings ========================

variable "project_id" {
  type        = string
  description = "The GCP project id"
  default     = "project"
}

variable "region" {
  type        = string
  description = "The GCP region to deploy resources"
  default     = "us-central1"
}

variable "zone" {
  type        = string
  description = "The GCP zone to deploy resources"
  default     = "us-central1-a"
}

variable "state_bucket" {
  type        = string
  description = "The terraform state bucket to load data from"
}

variable "public_key" {
  type = string
  description = "The public key to access the VM with the egoadmin user"
}

variable "python_repository" { 
  type = string
  description = "The python repository that stores "
}

# ======================== Network ========================

variable "network_from" {
  type = string
  description = "Wether or not to bootstrap using the base or standard terraform projects."

  validation {
    condition = contains(["base-instances","cluster-network"], var.network_from)
    error_message = "var.network_from should be either base-instances or cluster-network."
  }
}
