module "ops-agent-policy" {
  source     = "terraform-google-modules/cloud-operations/google//modules/ops-agent-policy"
  version = "0.6.0"
  project = var.project_id
  zone = var.zone
  assignment_id = "symphony-ops-agent-policy"

  agents_rule = {
    package_state = "installed"
    version = "latest"
  }

  instance_filter = {
    all = false

    inclusion_labels = [{
        labels = {
            goog-ops-agent-policy = "enabled"
        }
    }]
  }
}