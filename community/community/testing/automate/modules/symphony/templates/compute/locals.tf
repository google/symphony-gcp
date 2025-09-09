locals {
  # ==================================================================================================================================

  # Scripts
  common_functions                 = file("${path.module}/../scripts/common.sh")
  common_startup_scripts           = file("${path.module}/../scripts/sym-common.sh")
  compute_startup_script_functions = file("${path.module}/../scripts/compute_startup.sh")

  # Templates
  compute_template = (
    var.restore_compute_disk ?
    "${path.module}/../templates/compute_restore_script.tftpl" :
    "${path.module}/../templates/compute_startup_script.tftpl"
  )

}