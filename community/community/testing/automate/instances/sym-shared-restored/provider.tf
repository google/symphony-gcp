locals {
  module_suffix = terraform.workspace
}

# Configure the Google Cloud provider
provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone

  default_labels = {
    tf-workspace = local.module_suffix
    tf-project   = "sym-shared-restored"
  }
}

terraform {
  required_version = "~>1.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~>6.34.0"
    }
  }

  backend "gcs" {
    prefix = "sym-shared-restored"
  }
}

