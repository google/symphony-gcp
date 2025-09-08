data "terraform_remote_state" "base_state" {
  backend = "gcs"
  config = {
    bucket = var.state_bucket
    prefix = "base-instances"
  }
}