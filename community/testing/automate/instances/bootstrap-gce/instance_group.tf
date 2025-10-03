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

resource "google_compute_instance_group_manager" "hf-compute-manager" {
  name = "hf-sym-compute"

  base_instance_name = "hf-sym-compute"
  zone = var.zone

  version {
    instance_template = data.terraform_remote_state.symphony.outputs.symphony_compute_template_self_link
  }

  all_instances_config {
    metadata = local.metadata
    labels = {
      tf-workspace = local.module_suffix
      tf-project   = "sym-shared"
      resource-type = "hf-sym-compute"
    }
  }

  target_size = 1

  lifecycle {
    ignore_changes = [ target_size ]
  }

}