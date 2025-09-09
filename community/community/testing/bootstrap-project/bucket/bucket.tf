resource "google_storage_bucket" "main-bucket" {
  name          = var.state_bucket
  location      = "US"
  
  force_destroy = false

  public_access_prevention = "enforced"
  uniform_bucket_level_access = true
}