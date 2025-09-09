locals {
  grafana_namespace = "grafana"
  grafana_app       = "grafana"
}

# Create the grafana namespace
resource "kubernetes_namespace" "grafana" {
  metadata {
    name = local.grafana_namespace
  }
}

# Install Grafana using Helm
# WATCHOUT: If you have a `grafana` directory on your 
# project this WILL bug!
resource "helm_release" "grafana" {
  name       = "grafana"
  repository = "https://grafana.github.io/helm-charts"
  chart      = "grafana"
  namespace  = kubernetes_namespace.grafana.metadata[0].name
  create_namespace = false

  # Use values from your values.yaml file
  # https://github.com/grafana/helm-charts/blob/main/charts/grafana/values.yaml
  values = [
    yamlencode({
      persistence = {
        type    = "pvc"
        enabled = true
      }

      plugins = [
        "grafana-bigquery-datasource"
      ]

      rbac = {
        create = true
      }

      serviceAccount = {
        create = true
        annotations = {
          "iam.gke.io/gcp-service-account" = "${data.terraform_remote_state.orchestrator.outputs.orchestrator-sa-email}"
        }
        automountServiceAccountToken = true
      }

      "grafana.ini" = {
        dashboards = {
          min_refresh_interval = "1s"
        }
      }
    })
  ]

  # Ensure namespace is created first
  depends_on = [kubernetes_namespace.grafana]
}


data "kubernetes_secret" "grafana_password" {
  depends_on = [ helm_release.grafana ]
  metadata {
    name = local.grafana_app
    namespace = kubernetes_namespace.grafana.metadata[0].name
  }
}

output "grafana_admin_password" {
  value = nonsensitive(data.kubernetes_secret.grafana_password.data["admin-password"])
}