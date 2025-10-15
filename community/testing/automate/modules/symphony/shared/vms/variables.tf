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

variable "subnet_self_link" {
  type        = string
  description = "The subnet self link to be used by the NFS and cluster."
}

# ============================== SA ==============================

variable "service_account_mail" {
  type        = string
  description = "The service account to be used for the NFS and Symphony machines."
}

# ============================== NFS ==============================

variable "nfs_share" {
  type        = string
  description = "The NFS server share"
  default     = "/mnt/nfs-disk"
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


variable "nfs_disk_snapshot_self_link" {
  type        = string
  description = "The link to the snapshot to be restored on to the NFS disk."
  default     = null
}

variable "nfs_additional_subnets" {
  type = list(string)
  description = "Additional subnets to export the NFS"
  default = []
}

# ============================== Symphony ==============================

variable "install_only" {
  type        = bool
  description = "Only install Symphony. Do not start cluster. Defaults to false."
  default     = null
}

# ============================== Templates ==============================

variable "symphony_mgmt_template" {
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
      source_image = "rhel-cloud/rhel-8"
      type         = "pd-standard"
      size         = 30
    }
  }
}

variable "symphony_mgmt_replicas" {
  type = number
  default = 1
}

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
      type         = "pd-standard"
      source_image = "rhel-cloud/rhel-8"
    }
  }
}

variable "symphony_compute_replicas" {
  type = number
  default = 1
}

variable "restore_mgmt_disk" {
  type    = bool
  default = false
}

variable "restore_compute_disk" {
  type    = bool
  default = false
}

# ============================== Access ==============================

variable "public_key" {
  type        = string
  description = "The public SSH key to be used for access."
  sensitive   = true
}

# ============================== Labels ============================== 

variable "common_labels" {
  type = any
  description = "The labels to be applied to the machines of tqcdis module. Needs to be an object."
}

variable "cloudops_labels" {
  type = any
  description = "The cloudops policy label for installing the cloudops agent."
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
    SIMPLIFIEDWEM= string
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

    # Required if shared fs installation - Should be at shared directory
    SHARED_TOP = string

    EGO_ADMIN_USERNAME = string
    EGO_ADMIN_PASSWORD = string

    # Where to download the binaries
    SYM_BIN = string
    SYM_BIN_GCS_PATH = string
    SYM_ENTITLEMENT = string
    SYM_ENTITLEMENT_GCS_PATH = string

    CLUSTER_ADMIN_UID = string
    CLUSTER_ADMIN_GID = string

    # Required if shared fs installation
    MOUNT_POINT = string

    # Used to flag if the deployment was successful or not
    SUCCESS_TAG = string
    FAIL_TAG = string
  })
  default = {
    EGO_TOP = "/mnt/nfs/install"
    RPMDB_DIR = "/mnt/nfs/rpmdb"
    SHARED_TOP = "/mnt/nfs/install"
    EGO_ADMIN_USERNAME = "Admin"
    EGO_ADMIN_PASSWORD = "Admin"
    SYM_BIN = "/opt/ibm/bin/sym-7.3.2.0_x86_64.bin"
    SYM_BIN_GCS_PATH = "gs://symphony_bucket/sym-7.3.2.0_x86_64.bin"
    SYM_ENTITLEMENT = "/opt/ibm/bin/sym_732_adv_entitlement.dat"
    SYM_ENTITLEMENT_GCS_PATH = "gs://symphony_bucket/sym_732_adv_entitlement.dat"
    CLUSTER_ADMIN_UID = "10001"
    CLUSTER_ADMIN_GID = "10001"
    MOUNT_POINT = "/mnt/nfs/"
    SUCCESS_TAG = "startup-done"
    FAIL_TAG = "startup-fail"
  }
}

# ============================== Plugin Config ==============================

variable "python_repository" {
  type = string
  description = "The python repository to use for installation of the GKE CLI plugin. Format = $REGION-python.pkg.dev/$PROJECT/$REGISTRY"
}