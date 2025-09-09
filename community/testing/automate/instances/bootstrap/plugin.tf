
resource "kubernetes_namespace" "plugin-namespace" {
  metadata {
    name = var.plugin_namespace
  }
}

resource "kubernetes_service_account" "bootstrap-service-account" {
  metadata {
    name = "manifest-applier-sa"
  }
}

resource "kubernetes_role_binding" "bootstrap-role-binding" {

  metadata {
    name      = "manifest-applier-binding"
    namespace = kubernetes_namespace.plugin-namespace.metadata[0].name
  }
  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = "admin"
  }

  subject {
    kind = "ServiceAccount"
    name = kubernetes_service_account.bootstrap-service-account.metadata[0].name
  }

}

resource "kubernetes_cluster_role_binding" "bootstrap-role-binding" {

  metadata {
    name = "manifest-applier-role-binding"
  }
  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "ClusterRole"
    name      = "cluster-admin"
  }

  subject {
    kind = "ServiceAccount"
    name = kubernetes_service_account.bootstrap-service-account.metadata[0].name
  }

}

# Check if ConfigMap exists
data "kubernetes_config_map" "existing_operator_manifests" {
  count = var.job_cleanup_enabled ? 1 : 0

  metadata {
    name = local.operator-configmap-name
  }

  # This will fail if ConfigMap doesn't exist, so we handle it gracefully
  lifecycle {
    postcondition {
      condition     = self.data != null
      error_message = "ConfigMap does not exist"
    }
  }
}

resource "kubernetes_config_map" "proxy_kubeconfig" {
  metadata {
    namespace = kubernetes_namespace.plugin-namespace.metadata[0].name
    name = "kubeconfig"
  }

  data = {
    config = <<EOF
      example-config
    EOF
  }
  
}

resource "kubernetes_job_v1" "cleanup-hostfactory-operator" {
  count = can(data.kubernetes_config_map.existing_operator_manifests[0].data) && var.job_cleanup_enabled ? 1 : 0

  metadata {
    name = "cleanup-hostfactory-operator"
  }

  wait_for_completion = true

  timeouts {
    create = "360s"
    update = "360s"
    delete = "60s"
  }

  spec {
    template {
      metadata {
        name = "cleanup-hostfactory-operator"
      }
      spec {
        service_account_name = kubernetes_service_account.bootstrap-service-account.metadata[0].name
        restart_policy       = "Never"
        volume {
          name = "manifest-vol"
          config_map {
            name = local.operator-configmap-name
          }
        }
        affinity {
          node_affinity {
            required_during_scheduling_ignored_during_execution {
              node_selector_term {
                match_expressions {
                  key      = "node-pool"
                  operator = "In"
                  values = [
                    "base-pool",
                    "generic-pool"
                  ]
                }
              }
            }
          }
        }
        container {
          name    = "hostfactory-operator-cleanup"
          image   = "bitnami/kubectl:latest"
          command = ["sh", "-c"]
          volume_mount {
            name       = "manifest-vol"
            mount_path = "/manifests"
            read_only  = true
          }
          args = [
            <<-EOC
              set -e

              # Since the GCPSR manages the finalizers such that only the operator is able to terminate the pods,
              # we are required to use the GCPSR to delete the pods              

              echo "Using manifests from existing ConfigMap..."
              kubectl delete gcpsr --all -n ${kubernetes_namespace.plugin-namespace.metadata[0].name} --ignore-not-found=true

              echo "Waiting for pod deletion (300s)..."
              if ! kubectl wait --for=delete pod \
                -n ${kubernetes_namespace.plugin-namespace.metadata[0].name} \
                -l "managed-by=gcp-symphony-operator" \
                --timeout=300s; then
                echo "ERROR: Failed to delete all pods..." >&2 
                exit 1
              fi

              # TODO: Wait only for pods with the correct tag...

              kubectl delete rrm --all -n ${kubernetes_namespace.plugin-namespace.metadata[0].name} --ignore-not-found=true
                            
              # Delete resources using the mounted manifests
              kubectl delete -k /manifests --ignore-not-found=true

              echo "Cleanup completed"

            EOC
          ]
        }
      }
    }
  }
}

resource "kubernetes_job" "bootstrap-hostfactory-operator" {
  depends_on = [
    kubernetes_cluster_role_binding.bootstrap-role-binding,
    kubernetes_role_binding.bootstrap-role-binding,
    kubernetes_namespace.plugin-namespace,
    kubernetes_job_v1.cleanup-hostfactory-operator
  ]

  wait_for_completion = false

  metadata {
    name = "bootstrap-hostfactory-operator"
  }

  spec {
    template {
      metadata {
        name = "bootstrap-hostfactory-operator"
      }
      spec {
        service_account_name = kubernetes_service_account.bootstrap-service-account.metadata[0].name
        restart_policy       = "Never"
        volume {
          name = "manifest-vol"
          empty_dir {
            size_limit = "500Mi"
          }
        }
        affinity {
          node_affinity {
            required_during_scheduling_ignored_during_execution {
              node_selector_term {
                match_expressions {
                  key      = "node-pool"
                  operator = "In"
                  values = [
                    "base-pool",
                    "generic-pool"
                  ]
                }
              }
            }
          }
        }
        init_container {
          name = "hostfactory-operator-generator"
          volume_mount {
            name       = "manifest-vol"
            mount_path = "/manifests"
          }
          security_context {
            run_as_group = 0
            run_as_user  = 1001
          }
          env {
            name  = "GCP_HF_DEFAULT_NAMESPACES"
            value = kubernetes_namespace.plugin-namespace.metadata[0].name
          }
          image = "us-docker.pkg.dev/symphony-dev-2/hf-gcp-testing/k8s-operator:latest"
          args = [
            "export-manifests",
            "--separate-files",
            "/manifests"
          ]
        }
        container {
          name  = "hostfactory-operator-applier"
          image = "bitnami/kubectl:latest"
          volume_mount {
            name       = "manifest-vol"
            mount_path = "/manifests"
          }
          command = ["sh", "-c"]
          env {
            name  = "GCP_HF_DEFAULT_NAMESPACES"
            value = kubernetes_namespace.plugin-namespace.metadata[0].name
          }
          env {
            name = "GCP_HF_ENABLE_GKE_PREEMPTION_HANDLING"
            value = "${var.enable_preemption_handling}"
          }
          args = [
            <<-EOC

              echo "Creating kustomization.yaml file..."
              set -e
              cat <<EOF > /manifests/kustomization.yaml
              ${file(local.operator-kustomization)}
              %{ if var.enable_proxy }
                - path: operator-proxy-patch.yaml
              %{ endif }
              EOF

              echo "Creating operator-patch.yaml file..."
              cat <<EOF > /manifests/operator-patch.yaml
              ${file(local.operator-patch)}
              EOF

              cat <<EOF > /manifests/operator-proxy-patch.yaml
              ${file(local.operator-proxy-patch)}
              EOF

              echo "Creating operator-pdb.yaml file..."
              cat <<EOF > /manifests/operator-pdb.yaml
              ${file(local.operator-pdb)}
              EOF

              echo "Creating operator-priority.yaml file..."
              cat <<EOF > /manifests/operator-priority.yaml
              ${file(local.operator-priority)}
              EOF
              
              echo "Deleting old configmap..."
              kubectl delete configmap ${local.operator-configmap-name} \
                -n ${kubernetes_namespace.plugin-namespace.metadata[0].name} \
                --ignore-not-found=true

              echo "Creating new configmap..." 
              kubectl create configmap ${local.operator-configmap-name} \
                --from-file=/manifests/ \
                --dry-run=client -oyaml | kubectl apply -f -

              echo "Deploying new manifests..."
              kubectl get deployment gcp-symphony-operator \
                -n ${kubernetes_namespace.plugin-namespace.metadata[0].name} >/dev/null 2>&1 && \
                kubectl rollout restart deployment -n ${kubernetes_namespace.plugin-namespace.metadata[0].name} gcp-symphony-operator
              kubectl apply -k /manifests
              EOC
          ]
        }
      }
    }
  }

}
