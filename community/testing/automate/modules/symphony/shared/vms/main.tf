

resource "google_compute_instance_from_template" "symphony-mgmt" {
  count   = var.symphony_mgmt_replicas
  name    = "sym-shared-mgmt-${var.module_suffix}-${count.index}"
  project = var.project_id
  zone    = var.zone  
  
  labels = merge(
    {"resource-type" = "sym-mgmt-shared-node"},
    var.cloudops_labels,
    var.common_labels
  )

  # When the startup template supports 
  # multiple mgmt nodes, this will require overwrite
  # instead of merge...
  metadata = merge(
    {"STARTUP_INDEX" = count.index},
    # This creates a list divided by "," of the secondary hostnames...
    count.index != 0 ? {} : {"SECONDARY_NODES": join(",", [for i in range(1,var.symphony_mgmt_replicas) : "sym-shared-mgmt-${var.module_suffix}-${i}"])},
    module.symphony_mgmt_template.mgmt_metadata
  )
  
  metadata_startup_script = module.symphony_mgmt_template.mgmt_metadata_startup_script
  source_instance_template = module.symphony_mgmt_template.mgmt_template_self_link_unique

  depends_on = [module.nfs_server]
}

resource "google_compute_instance_from_template" "symphony-compute" {
  count   = var.symphony_compute_replicas
  name    = "sym-shared-compute-${var.module_suffix}-${count.index}"
  project = var.project_id
  zone    = var.zone

  labels = merge(
    {"resource-type" = "sym-compute-shared-node"},
    var.cloudops_labels,
    var.common_labels
  )

  source_instance_template = module.symphony_compute_template.compute_template_self_link_unique

  depends_on = [module.nfs_server]
}