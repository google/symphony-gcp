# ======================== Google Settings ========================

variable "project_id" {
  type        = string
  description = "The GCP project id"
  default     = "project"
}

variable "region" {
  type        = string
  description = "The GCP region to deploy resources"
  default     = "us-central1"
}

variable "zone" {
  type        = string
  description = "The GCP zone to deploy resources"
  default     = "us-central1-a"
}

variable "state_bucket" {
  type        = string
  description = "The terraform state bucket to load data from"
}

variable "kube_proxy_url" {
  type        = string
  description = "The url of the proxy for accessing the cluster"
}