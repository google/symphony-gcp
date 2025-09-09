# Configure the Google Cloud provider
provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone

  default_labels = {
    tf-workspace = local.module_suffix
    tf-project   = "cluster-base"
  }
}

locals {
  module_suffix = "test"
}

terraform {
  required_version = "~>1.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~>6.48.0"
    }

    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~>6.48.0"
    }
  }

  backend "gcs" {
    prefix = "cluster-base"
  }
}

