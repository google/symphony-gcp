locals {
  metadata = contains(["sym-local-restored", "sym-local"], var.target_symphony_project) ? {
  PRIMARY_HOSTNAME = "${data.google_compute_instance.master.name}.${data.google_compute_instance.master.zone}.c.${var.project_id}.internal"} : {}
}

data "google_compute_instance" "master" {
  self_link = data.terraform_remote_state.symphony.outputs.symphony_mgmt_vms_self_link[0]
}

# For a production environment with failover, in case of a local compute node,
# the Compute MIG should have a way of automatically 
# finding which is the master. This should be done by externalizing the master address storage (for example,
# using the MIG stateful metadata ) and implementing a script on which the secondary-masters continuously 
# query to see if they have become the leader (primary), and if so, then 
# the new leader changes the value of the stateful metadata.
# This would also require configuring a health check to eventually kill 
# any compute nodes which failed to join the master by using a stale address.
# More inteligently, if Symphony allows it, one could create a webhook (maybe as cloud run functions)
# in the event of failover to execute the master stateful metadata modification. 

data "google_compute_instance_template" "default_compute_template" {
  self_link_unique = data.terraform_remote_state.symphony.outputs.symphony_compute_template_self_link
}

module "symphony_compute_templates" {
  for_each = {for x in var.compute_templates: x.name => x }
  source = "../../modules/symphony/templates/compute"
  module_suffix = "${local.module_suffix}-${each.value.name}"

  project_id = var.project_id
  region = var.region

  # Service Account
  service_account_mail = data.google_compute_instance_template.default_compute_template.service_account[0].email
  
  # Network
  subnet_self_link = data.google_compute_instance_template.default_compute_template.network_interface[0].subnetwork

  # Config
  configuration_variables = data.terraform_remote_state.symphony.outputs.symphony_template_configuration_vars
  install_only = false

  # Templates
  symphony_compute_template = {
    disk = {
      size = each.value.disk_size
      type = each.value.disk_type
      source_image = data.google_compute_instance_template.default_compute_template.disk[0].source_image
    }
    machine_type = each.value.machine_type
  }

  # Restore Images
  restore_compute_disk = true

  common_labels = data.google_compute_instance_template.default_compute_template.labels

  public_key = var.public_key
}


resource "google_compute_instance_group_manager" "hf-compute-manager" {
  for_each = {for x in var.compute_templates: x.name => x }
  name = "sym-comp-${local.module_suffix}-${each.value.name}"

  base_instance_name = "sym-comp-${local.module_suffix}-${each.value.name}"
  zone = each.value.zone

  version {
    instance_template = module.symphony_compute_templates[each.key].compute_template_self_link_unique
  }

  all_instances_config {
    metadata = local.metadata
    labels = {
      tf-workspace = local.module_suffix
      tf-project   = "bootstrap-gce"
      resource-type = "hf-sym-compute"
    }
  }

  lifecycle {
    ignore_changes = [ target_size ]
  }

}