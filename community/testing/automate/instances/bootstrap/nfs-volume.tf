locals {
  is_shared_installation = contains(["sym-shared-restored","sym-shared"], var.target_symphony_project)
  nfs_disk_capacity = (
    local.is_shared_installation ?
    "${data.terraform_remote_state.symphony.outputs.nfs_disk_capacity}Gi" :
    null
  )
  nfs_server = (
    local.is_shared_installation ?
    data.terraform_remote_state.symphony.outputs.nfs_server_internal_ip : 
    null
  )
  nfs_path = (
    local.is_shared_installation ?
    data.terraform_remote_state.symphony.outputs.nfs_disk_mount_point : 
    null
  )
}

resource "kubernetes_persistent_volume" "nfs_persistent_volume" {
  count = local.is_shared_installation ? 1 : 0
  metadata {
    name = "pv-nfs"
  }

  spec {
    access_modes = ["ReadWriteMany"]
    capacity = {
      storage = local.nfs_disk_capacity
    }

    claim_ref {
      namespace = kubernetes_namespace.plugin-namespace.metadata[0].name
      name      = "pvc-nfs"
    }

    persistent_volume_source {
      nfs {
        server = local.nfs_server
        path   = local.nfs_path
      }
    }
  }
}

resource "kubernetes_persistent_volume_claim" "nfs_pvc" {
  count = local.is_shared_installation ? 1 : 0
  depends_on = [ kubernetes_persistent_volume.nfs_persistent_volume[0] ]
  
  metadata {
    name      = "pvc-nfs"
    namespace = kubernetes_namespace.plugin-namespace.metadata[0].name
  }

  lifecycle { 
    replace_triggered_by = [
      kubernetes_persistent_volume.nfs_persistent_volume[0]
    ]
  }

  spec {
    storage_class_name = ""
    volume_name        = "pv-nfs"
    access_modes       = ["ReadWriteMany"]
    resources {
      requests = {
        storage : local.nfs_disk_capacity
      }
    }
  }
}