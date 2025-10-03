# Configure the Google Cloud provider
provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone

  default_labels = {
    tf-workspace = local.module_suffix
    tf-project   = "bootstrap-gce"
  }
}

locals {
  module_suffix = terraform.workspace
}

terraform {
  required_version = "~>1.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~>6.40.0"
    }

    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~>6.40.0"
    }
  }

  backend "gcs" {
    prefix = "bootstrap-gce"
  }
}

