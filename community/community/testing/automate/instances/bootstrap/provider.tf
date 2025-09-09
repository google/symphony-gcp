# Configure the Google Cloud provider
provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone

  default_labels = {
    tf-workspace = local.module_suffix
    tf-project   = "bootstrap-cluster"
  }
}

# google_client_config and kubernetes provider must be explicitly specified like the following.
data "google_client_config" "default" {}

provider "kubernetes" {
  proxy_url              = var.kube_proxy_url
  host                   = "https://${local.cluster_data.endpoint}"
  token                  = data.google_client_config.default.access_token
  client_certificate     = base64decode(local.cluster_data.master_auth[0].client_certificate)
  client_key             = base64decode(local.cluster_data.master_auth[0].client_key)
  cluster_ca_certificate = base64decode(local.cluster_data.master_auth[0].cluster_ca_certificate)
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

    kubernetes = {
      source = "hashicorp/kubernetes"
      version = "~>2.37.0"
    }
  }

  backend "gcs" {
    prefix = "bootstrap-cluster"
  }
}

