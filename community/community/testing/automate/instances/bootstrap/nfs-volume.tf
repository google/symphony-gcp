locals {
  nfs_disk_capacity = "${data.terraform_remote_state.symphony.outputs.nfs_disk_capacity}Gi"
}

resource "kubernetes_persistent_volume" "nfs_persistent_volume" {

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
        server = data.terraform_remote_state.symphony.outputs.nfs_server_internal_ip
        path   = data.terraform_remote_state.symphony.outputs.nfs_disk_mount_point
      }
    }
  }
}

resource "kubernetes_persistent_volume_claim" "nfs_pvc" {
  depends_on = [ kubernetes_persistent_volume.nfs_persistent_volume ]
  
  metadata {
    name      = "pvc-nfs"
    namespace = kubernetes_namespace.plugin-namespace.metadata[0].name
  }

  lifecycle { 
    replace_triggered_by = [
      kubernetes_persistent_volume.nfs_persistent_volume
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