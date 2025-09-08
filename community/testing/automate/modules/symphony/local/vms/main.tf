# TODO: the primary hostname variable propagation is problematic (overall for management hosts) when using templates. 
# Need to find a better way to propagate it.

data "google_compute_instance_template" "mgmt_template" {
  self_link_unique = module.symphony_mgmt_template.mgmt_template_self_link_unique
}

data "google_compute_instance_template" "compute_template" {
  self_link_unique = module.symphony_compute_template.compute_template_self_link_unique
}

# TODO: Implement multi-management node startup syncronization (i.e. wait for master to be ready...)
# Also test if multiple compute nodes work...

resource "google_compute_instance_from_template" "symphony-mgmt-primary" {
  count   = var.symphony_mgmt_replicas
  name    = "sym-local-mgmt-${var.module_suffix}-${count.index}"
  project = var.project_id
  zone    = var.zone

  metadata = merge(
    data.google_compute_instance_template.mgmt_template.metadata,
    {PRIMARY_HOSTNAME = count.index == 0 ? "ME" : "sym-local-mgmt-${var.module_suffix}-0" }
  )

  labels = merge(
    {"resource-type" = "sym-mgmt-local-node"},
    var.cloudops_labels,
    var.common_labels
  )

  source_instance_template = module.symphony_mgmt_template.mgmt_template_self_link_unique
}


resource "google_compute_instance_from_template" "symphony-compute" {
  count   = var.symphony_compute_replicas
  name    = "sym-local-compute-${var.module_suffix}-${count.index}"
  project = var.project_id
  zone    = var.zone

  source_instance_template = module.symphony_compute_template.compute_template_self_link_unique

  labels = merge(
    {"resource-type" = "sym-compute-local-node"},
    var.cloudops_labels,
    var.common_labels
  )

  metadata = merge(data.google_compute_instance_template.compute_template.metadata, {
    PRIMARY_HOSTNAME = "${google_compute_instance_from_template.symphony-mgmt-primary[0].name}.${var.zone}.c.${var.project_id}.internal"
  })

  depends_on = [google_compute_instance_from_template.symphony-mgmt-primary]
}