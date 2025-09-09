# Configure the Google Cloud provider
provider "google" {
  project = var.project_id
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
    prefix = "bootstrap-project"
  }
}
