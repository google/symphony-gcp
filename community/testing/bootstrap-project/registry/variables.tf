# ============================== Project ==============================

variable "project_id" {
  type        = string
  description = "The GCP project ID"
}

variable "python_registry" {
  type        = string
  description = "The name of the python registry"
}

variable "docker_registry" {
  type        = string
  description = "The name of the docker registry"
}

variable "python_registry_location" {
  type        = string
  description = "The location of the python registry"
}

variable "docker_registry_location" {
  type        = string
  description = "The location of the docker registry"
}