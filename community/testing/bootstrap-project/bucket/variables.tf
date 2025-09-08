# ============================== Project ==============================

variable "project_id" {
  type        = string
  description = "The GCP project ID"
}

variable "state_bucket" {
  type        = string
  description = "The bucket to store the data"
}