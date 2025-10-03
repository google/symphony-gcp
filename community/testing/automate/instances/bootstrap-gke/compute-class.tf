locals {
  manifests_dir = "./compute-classes"
  manifests_fileset = [
    for filename in fileset(local.manifests_dir, "*.yaml") : "${filename}"
  ]
  manifests = [
    for filename in local.manifests_fileset : "${local.manifests_dir}/${filename}"
  ]
}

# Actually not necessarily but mainly compute classes...
resource "kubernetes_manifest" "compute_classes" {
  for_each = toset(local.manifests)
  manifest = yamldecode(file(each.key))
}