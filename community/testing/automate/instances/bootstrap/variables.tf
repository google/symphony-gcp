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

variable "kube_proxy_url" {
  type        = string
  description = "The url of the proxy for accessing the cluster"
}

# ============================== Registry ==============================

variable "docker_repository" {
  type        = string
  description = "The docker registry server to be used for the Symphony images"
}

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

variable "target_symphony_shared_workspace" {
  type = string
  description = "The target Symphony Shared terraform workspace to bootstrap."
}

variable "target_cluster_workspace" {
  type = string
  description = "The target Symphony Shared terraform workspace to bootstrap."
}

# ============================== Other ==============================

variable "job_cleanup_enabled" {
  type = bool
  description = "Wether or not to trigger the cleanup job if the manifests configmap exist."
  default = false
}

variable "enable_proxy" {
  type = bool
  description = "Wether or not to enable proxying the operator."
  default = false
}

# ============================= CCC =============================

variable "enable_ccc" {
  type = bool
  description = "Enable the CCC which automatically sources from the cluster-base project."
  default = true
}

variable "nodepool_autoscaler" {
  type = bool
  description = "Enable node pool auto creation in the CCC."
  default = true
}

variable "autoscaling_groups" {
  type = list(any)
  description = "List of autoscaling families to apply to the CCC."
  default = []
}

variable "secondary_boot_disks" {
  type = list(string)
  description = "Secondary boot disk name. If null, then disabled."
} 

# ============================== Run ID ==============================

variable "run_id" {
  type = any # string || null
  description = "The run id to tag the resources with."
  default = null
}

# ============================== Plugin ==============================

variable "enable_preemption_handling" {
  type = string
  description = "Wether or not to enable preemption handling. Can be either `True` or `False`."
  default = "True"

  validation {
    condition = contains(["True","False"], var.enable_preemption_handling)
    error_message = "var.enable_preemption_handling should be either `True` or `False`."
  }
}
