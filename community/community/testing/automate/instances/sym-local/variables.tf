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
# ============================== Access ==============================

variable "public_key" {
  type        = string
  description = "The public SSH key to be used for access."
  sensitive   = true
}

# ============================== Install Options ==============================

variable "install_only" {
  type        = bool
  description = "If true, does not bootstrap Symphony cluster and does not start it."
  default     = false
}

# ============================== Symphony Management ==============================

variable "symphony_mgmt_template" {
  type = object({
    machine_type = string
    disk = object({
      source_image = string
      type = string
      size = number 
    })
  })
  default = {
    machine_type = "n2-standard-2"
    disk = {
      source_image = "rhel-cloud/rhel-8"
      type         = "pd_standard"
      size         = 30
  }
}
}

variable "symphony_mgmt_replicas" {
  type = number
  default = 1
}


# ============================== Symphony Compute ==============================

variable "symphony_compute_template" {
  type = object({
    machine_type = string
    disk = object({
      source_image = string
      type = string
      size = number 
    })
  })
  default = {
    machine_type = "n2-standard-2"
    disk = {
      source_image = "rhel-cloud/rhel-8"
      type         = "pd_standard"
      size         = 30
  }
}
}

variable "symphony_compute_replicas" {
  type = number
  default = 1
}

# ============================== Main Variables ==============================

variable "symphony_vars" {
  type = object({
    # ================================= ISS Variables =================================

    # Mandatory if install as root. Needs to be any valid operating user account.
    CLUSTERADMIN = string 
    # Optional. Default = 7869. The system uses 7 consecutive ports from the base port
    BASEPORT = string 
    # Optional. Required if using simplified WEM.
    SIMPLIFIEDWEM = string
    # Required if doing silent installation.
    IBM_SPECTRUM_SYMPHONY_LICENSE_ACCEPT = string 
    # Optional. Default = N ; If one wishes to disable SSL.
    DISABLESSL = string 
    # Optional. Default = cluster1.
    CLUSTERNAME = string 
  })

  default = {
    # Mandatory if install as root. Needs to be any valid operating user account.
    CLUSTERADMIN = "egoadmin"
    # Optional. Default = 7869. The system uses 7 consecutive ports from the base port
    BASEPORT = "17869"
    # Optional. Required if using simplified WEM.
    SIMPLIFIEDWEM = "N"
    # Required if doing silent installation.
    IBM_SPECTRUM_SYMPHONY_LICENSE_ACCEPT = "Y"
    # Optional. Default = N ; If one wishes to disable SSL.
    DISABLESSL = "Y"
    # Optional. Default = cluster1.
    CLUSTERNAME = "test-cluster"
  }
}

variable "auxiliary_startup_vars" {
  type = object({
    # ================================= Auxiliary Variables =================================
    
    # Symphony Installation path - Should be at shared directory
    EGO_TOP = string
    RPMDB_DIR = string

    EGO_ADMIN_USERNAME = string
    EGO_ADMIN_PASSWORD = string

    # Where to download the binaries
    SYM_BIN = string
    SYM_BIN_GCS_PATH = string
    SYM_ENTITLEMENT = string
    SYM_ENTITLEMENT_GCS_PATH = string

    CLUSTER_ADMIN_UID = string
    CLUSTER_ADMIN_GID = string

    # Used to flag if the deployment was successful or not
    SUCCESS_TAG = string
    FAIL_TAG = string
  })
  
  default = {
    EGO_TOP = "/opt/ibm/spectrumcomputing"
    RPMDB_DIR = "/var/lib/rpm"
    EGO_ADMIN_USERNAME = "Admin"
    EGO_ADMIN_PASSWORD = "Admin"
    SYM_BIN = "/opt/ibm/bin/sym-7.3.2.0_x86_64.bin"
    SYM_BIN_GCS_PATH = "gs://symphony_bucket/sym-7.3.2.0_x86_64.bin"
    SYM_ENTITLEMENT = "/opt/ibm/bin/sym_732_adv_entitlement.dat"
    SYM_ENTITLEMENT_GCS_PATH = "gs://symphony_bucket/sym_732_adv_entitlement.dat"
    CLUSTER_ADMIN_UID = "10001"
    CLUSTER_ADMIN_GID = "10001"
    SUCCESS_TAG = "startup-done"
    FAIL_TAG = "startup-fail"
  }
}

# ============================== Plugin Config ==============================

variable "python_repository" {
  type = string
  description = "The python repository to use for installation of the GKE CLI plugin. Format = $REGION-python.pkg.dev/$PROJECT/$REGISTRY"
}

# ============================== Network ==============================

variable "network_from" {
  type = string
  default = "base-instances"
  description = "Wether or not to bootstrap using the base or standard terraform projects."

  validation {
    condition = contains(["base-instances","cluster-network"], var.network_from)
    error_message = "var.network_from should be either base-instances or cluster-network."
  }
}

variable "cluster_index" {
  type = number
  description = "The cluster index to bootstrap if using 'cluster-base'. Not required if using 'cluster-standard'."
  default = null
}