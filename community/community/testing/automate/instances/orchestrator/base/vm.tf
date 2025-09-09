resource "google_compute_instance" "orchestrator" {
  name         = "orchestrator-${local.module_suffix}"
  machine_type = "n2-standard-2"
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "rhel-cloud/rhel-8"
      type  = "pd-standard"
      size  = 60
    }
  }

  network_interface {
    network    = local.network
    subnetwork = local.vm_subnet_self_link
  }

  service_account {
    email = data.terraform_remote_state.base_state.outputs.service_account.email
    scopes = ["cloud-platform"]
  }

  metadata = {
    enable-oslogin = "FALSE"
    ssh-keys = <<EOF
      egoadmin:${var.public_key}
    EOF
  }

  metadata_startup_script = <<EOF
    DEPENDENCIES=(
        python3.12 
        kubectl
        google-cloud-sdk-gke-gcloud-auth-plugin
    )

    yum install -y "$${DEPENDENCIES[@]}"

    python3.12 -m ensurepip
    python3.12 -m pip install --upgrade pip
    python3.12 -m pip install uv

    python3.12 -m uv tool install \
      --index=https://oauth2accesstoken:$(gcloud auth print-access-token)@${var.python_repository}/simple proxy

  EOF
}

