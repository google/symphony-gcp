resource "kubernetes_manifest" "compute_class" {
  count = var.enable_ccc ? 1 : 0
  manifest = {
    apiVersion = "cloud.google.com/v1"
    kind       = "ComputeClass"
    metadata = {
      name = data.terraform_remote_state.cluster_output.outputs.compute_class
    }
    spec = {
      # Automatically creates priority specification from cluster-base node pools specification.
      priorities = concat(
        [
          for pool in data.terraform_remote_state.cluster_output.outputs.compute_class_node_pools : 
          { "nodepools" = [pool] }
        ],
        # Adds the autoscaling families variable respecting the given order
        # Enable secondary boot disk...
        var.autoscaling_groups
      )
      autoscalingPolicy = {
        consolidationDelayMinutes = 1
        consolidationThreshold = 1
      }
      activeMigration = {
        optimizeRulePriority = false
      }
      nodePoolAutoCreation = {
        enabled = var.nodepool_autoscaler
      }
      whenUnsatisfiable = "DoNotScaleUp"
    }
  }
}

resource "kubernetes_manifest" "allow_secondary" {
  count = (length(var.secondary_boot_disks) != 0 && var.enable_ccc) ? 1 : 0
  manifest = {
    apiVersion = "node.gke.io/v1"
    kind = "GCPResourceAllowlist"
    metadata = {
      name = "gke-secondary-boot-disk-allowlist"
    }
    spec = {
      allowedResourcePatterns = [
        for secondary_boot_disk in var.secondary_boot_disks: "projects/${var.project_id}/global/images/${secondary_boot_disk}"
      ]
    }
  }

  
}