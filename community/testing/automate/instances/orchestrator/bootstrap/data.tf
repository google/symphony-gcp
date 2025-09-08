data "terraform_remote_state" "base_state" {
  backend = "gcs"
  config = {
    bucket = var.state_bucket
    prefix = "base-instances"
  }
}

data "terraform_remote_state" "orchestrator" {
  backend = "gcs"
  config = {
    bucket = var.state_bucket
    prefix = "orchestrator-base"
  }
}