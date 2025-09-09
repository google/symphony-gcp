locals {
  common_vars = {
    # ================================= Auxiliary Variables =================================

    # Symphony Installation path - default 
    EGO_TOP   = "/opt/ibm/spectrumcomputing"
    RPMDB_DIR = " /var/lib/rpm"

    EGO_ADMIN_USERNAME = "Admin"
    EGO_ADMIN_PASSWORD = "Admin"

    # Where to download the binaries
    SYM_BIN         = "/opt/ibm/bin/sym-7.3.2.0_x86_64.bin"
    SYM_ENTITLEMENT = "/opt/ibm/bin/sym_732_adv_entitlement.dat"

    CLUSTER_ADMIN_UID = "10001"
    CLUSTER_ADMIN_GID = "10001"

    # This needs to be declared using environment variables...
    # PRIMARY_HOSTNAME = var.primary_hostname

    # Used to flag if the deployment was successful or not
    SUCCESS_TAG = "startup-done"
    FAIL_TAG    = "startup-fail"

    # # TODO: Add key injection in container
    # # SSH Authorization 
    # PUB_KEY = var.public_key

    # ================================= ISS Variables =================================

    # Mandatory if install as root. Needs to be any valid operating user account.
    CLUSTERADMIN = "egoadmin"
    # Optional. Default = 7869. The system uses 7 consecutive ports from the base port
    BASEPORT = "17869"
    # Optional. Required if using simplified WEM.
    # SIMPLIFIEDWEM="N"
    # Required if doing silent installation.
    IBM_SPECTRUM_SYMPHONY_LICENSE_ACCEPT = "Y"
    # Optional. Default = N ; If one wishes to disable SSL.
    DISABLESSL = "Y"
    # Optional. Default = cluster1.
    CLUSTERNAME = "development"
    # CLUSTERNAME = var.cluster_name
    # Optional. Required value "Y" if shared fs install
    SHARED_FS_INSTALL = "N"
  }
}

locals {
  common_functions                 = file("${path.module}/../../../../scripts/common.sh")
  common_startup_scripts           = file("${path.module}/../scripts/sym-common.sh")
  mgmt_startup_script_functions    = file("${path.module}/../scripts/mgmt_startup.sh")
  compute_startup_script_functions = file("${path.module}/../scripts/compute_startup.sh")
}

resource "local_file" "startup_script" {
  filename = "${path.module}/startup.sh"
  content = templatefile("${path.module}/startup.tftpl", {
    common_vars              = local.common_vars
    common_functions         = local.common_functions
    common_startup_scripts   = local.common_startup_scripts
    startup_script_functions = local.compute_startup_script_functions

    environment_variables = {
      EGOCOMPUTEHOST = "Y"
    }

    install_only = true
  })
}