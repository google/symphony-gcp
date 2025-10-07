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

# ============================== Registry ==============================

variable "python_repository" {
  type        = string
  description = "The python registry server to be used for the Symphony plugin"
}

variable "plugin_namespace" {
  type        = string
  description = "The plugin namespace to be automatically created and injected with the credentials"
  default     = "gcp-symphony"
}

variable "private_key_path" {
  type = string
  description = "The private key of the clusteradmin user"
}

# ============================== Bootstrap target ==============================

variable "bootstrap_from" {
  type = string
  default = "cluster-standard"
  description = "Wether or not to bootstrap using the base or standard terraform projects."

  validation {
    condition = contains(["cluster-standard","cluster-base"], var.bootstrap_from)
    error_message = "var.bootstrap_from should be either cluster-standard or cluster-base."
  }
}

variable "target_symphony_project" {
  type = string
  description = "The target Symphony terraform project to boostrap. Accepted values are: sym-shared-restored, sym-shared and sym-local."
  default = "sym-shared-restored"

  validation {
    condition = contains(["sym-shared-restored","sym-shared", "sym-local", "sym-local-restored"], var.target_symphony_project)
    error_message = "var.target_symphony_project invalid."
  }
}

variable "target_symphony_workspace" {
  type = string
  description = "The target Symphony terraform workspace to bootstrap."
}

# ============================== Run ID ==============================

variable "run_id" {
  type = any # string || null
  description = "The run id to tag the resources with."
  default = null
}