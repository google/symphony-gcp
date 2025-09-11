
locals {
  module_suffix = terraform.workspace
}

data "terraform_remote_state" "ephemeral" {
  backend   = "gcs"
  workspace = local.module_suffix
  config = {
    bucket = var.state_bucket
    prefix = "sym-local"
  }
}

data "google_compute_instance" "mgmt_vm" {
  self_link = data.terraform_remote_state.ephemeral.outputs.symphony_mgmt_vms_self_link[0]
}

data "google_compute_instance" "compute_vm" {
  self_link = data.terraform_remote_state.ephemeral.outputs.symphony_compute_vms_self_link[0]
}


resource "null_resource" "startup_finished" {
  provisioner "local-exec" {
    interpreter = ["bash", "-c"]
    command     = <<-EOF

    # ===== Variables =====
    set -eo pipefail

    # Project
    export REGION=${var.region}
    export ZONE=${var.zone}

    # Targets
    export MGMT_INSTANCE=${data.terraform_remote_state.ephemeral.outputs.symphony_mgmt_vms_names[0]}
    export COMPUTE_INSTANCE=${data.terraform_remote_state.ephemeral.outputs.symphony_compute_vms_names[0]}

    ${file("./wait-disown-stop.sh")}

    EOF
  }
}

resource "google_compute_image" "mgmt_image" {
  name        = "sym-local-mgmt-${local.module_suffix}"
  source_disk = data.google_compute_instance.mgmt_vm.boot_disk[0].source

  depends_on = [null_resource.startup_finished]

}

resource "google_compute_image" "compute_image" {
  name        = "sym-local-compute-${local.module_suffix}"
  source_disk = data.google_compute_instance.compute_vm.boot_disk[0].source

  depends_on = [null_resource.startup_finished]

}