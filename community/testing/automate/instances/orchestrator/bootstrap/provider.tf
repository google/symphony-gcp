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
    tf-project   = "orchestrator-bootstrap"
  }
}

# google_client_config and kubernetes provider must be explicitly specified like the following.
data "google_client_config" "default" {}

data "google_container_cluster" "cluster" {
  name     =  data.terraform_remote_state.orchestrator.outputs.cluster-name
  location =  data.terraform_remote_state.orchestrator.outputs.cluster-location
}

provider "kubernetes" {
  proxy_url              = var.kube_proxy_url
  host                   = "https://${data.google_container_cluster.cluster.endpoint}"
  token                  = data.google_client_config.default.access_token
  client_certificate     = base64decode(data.google_container_cluster.cluster.master_auth[0].client_certificate)
  client_key             = base64decode(data.google_container_cluster.cluster.master_auth[0].client_key)
  cluster_ca_certificate = base64decode(data.google_container_cluster.cluster.master_auth[0].cluster_ca_certificate)
}

provider "helm" {
  kubernetes = {
      proxy_url              = var.kube_proxy_url
      host                   = "https://${data.google_container_cluster.cluster.endpoint}"
      token                  = data.google_client_config.default.access_token
      client_certificate     = base64decode(data.google_container_cluster.cluster.master_auth[0].client_certificate)
      client_key             = base64decode(data.google_container_cluster.cluster.master_auth[0].client_key)
      cluster_ca_certificate = base64decode(data.google_container_cluster.cluster.master_auth[0].cluster_ca_certificate)
  }
}

terraform {

  required_version = "~>1.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~>6.34.0"
    }

    kubernetes = {
      source = "hashicorp/kubernetes"
      version = "~>2.37.0"
    }

    helm = {
      source = "hashicorp/helm"
      version = "~>3.0.2"
    }
  }

  backend "gcs" {
    prefix = "orchestrator-bootstrap"
  }
}

