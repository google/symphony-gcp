locals {
  # ==================================================================================================================================

  # Scripts
  common_functions              = file("${path.module}/../scripts/common.sh")
  common_startup_scripts        = file("${path.module}/../scripts/sym-common.sh")
  mgmt_startup_script_functions = file("${path.module}/../scripts/mgmt_startup.sh")

  mgmt_template = (
    var.restore_mgmt_disk ?
    "${path.module}/../templates/mgmt_restore_script.tftpl" :
    "${path.module}/../templates/mgmt_startup_script.tftpl"
  )

}