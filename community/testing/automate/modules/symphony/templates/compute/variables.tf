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

# ============================== SA ==============================

variable "service_account_mail" {
  type        = string
  description = "The service account to be associated with the template."
}

# ============================== Network ==============================

variable "subnet_self_link" {
  type        = string
  description = "The subnet to be associated with the template."
}

# ============================== Symphony ==============================

variable "install_only" {
  type        = bool
  description = "Only install Symphony. Do not start cluster. Defaults to false."
  default     = null
}

# ============================== Templates ==============================

variable "symphony_compute_template" {
  type = object({
    machine_type = string
    disk = object({
      source_image = string
      type         = string
      size         = number
    })
  })
  default = {
    machine_type = "n2-standard-2"
    disk = {
      size         = 30
      type         = "pd_standard"
      source_image = "rhel-cloud/rhel-8"
    }
  }
}


variable "restore_compute_disk" {
  type    = bool
  default = false
}

# ============================== Common Variables ==============================

variable "configuration_variables" {
  type = object({
    EGO_TOP                              = string
    SHARED_TOP                           = optional(string)
    RPMDB_DIR                            = optional(string)
    EGO_ADMIN_USERNAME                   = string
    EGO_ADMIN_PASSWORD                   = string
    SYM_BIN                              = string
    SYM_BIN_GCS_PATH                     = string
    SYM_ENTITLEMENT                      = string
    SYM_ENTITLEMENT_GCS_PATH             = string
    CLUSTER_ADMIN_UID                    = string
    CLUSTER_ADMIN_GID                    = string
    NFS_IP                               = optional(string)
    NFS_SHARE                            = optional(string)
    MOUNT_POINT                          = optional(string)
    PRIMARY_HOSTNAME                     = optional(string)
    SUCCESS_TAG                          = string
    FAIL_TAG                             = string
    PUB_KEY                              = string
    CLUSTERADMIN                         = string
    BASEPORT                             = string
    IBM_SPECTRUM_SYMPHONY_LICENSE_ACCEPT = string
    DISABLESSL                           = string
    CLUSTERNAME                          = string
    SHARED_FS_INSTALL                    = string
  })
  description = "The variables used to configure the Symphony installation."
}

# PRIMARY_HOSTNAME can be empty if it is the primary host installation..
# check "local_environment_coherence" {
#   assert {
#     condition = (
#       var.configuration_variables.SHARED_FS_INSTALL != "Y" && var.configuration_variables.PRIMARY_HOSTNAME != null
#     )
#     error_message = "Configuration error: shared_environment is false but primary_hostname is null."
#   }
# }

check "shared_environment_coherence" {
  assert {
    condition = (
      var.configuration_variables.SHARED_FS_INSTALL == "Y" && var.configuration_variables.NFS_IP != null && var.configuration_variables.NFS_SHARE != null ||
      var.configuration_variables.SHARED_FS_INSTALL != "Y" && var.configuration_variables.NFS_IP == null && var.configuration_variables.NFS_SHARE == null
    )
    error_message = "Configuration error: shared_environment variable is incoherent with nfs_ip and nfs_share variables"
  }
}

# ============================== Access ==============================

variable "public_key" {
  type        = string
  description = "The public SSH key to be used for access."
  sensitive   = true
}

variable "common_labels" {
  type = any
  description = "The labels to be applied to the machines of tqcdis module. Needs to be an object."
  default = {
    goog-ops-agent-policy = "enabled"
  }
}