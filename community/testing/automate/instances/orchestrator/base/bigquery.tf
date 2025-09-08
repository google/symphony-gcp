locals {
  schemas_dir = "${path.module}/bigquery-schemas"
  schemas = {
    for fn in fileset(local.schemas_dir, "*.json"): trimsuffix(fn,".json") => "${local.schemas_dir}/${fn}"
  }
}

resource "google_bigquery_dataset" "orchestrator" {
  dataset_id = "log_dataset_${local.module_suffix}"
  location   = var.region
}

resource "google_bigquery_table" "orchestrator" {
  for_each = local.schemas
  dataset_id = google_bigquery_dataset.orchestrator.dataset_id
  table_id   = each.key
  schema     = file(each.value)
  clustering = ["run"]
  deletion_protection = false
}

resource "google_bigquery_table_iam_member" "orchestrator" {
  for_each = local.schemas
  dataset_id = google_bigquery_table.orchestrator[each.key].dataset_id
  table_id   = google_bigquery_table.orchestrator[each.key].table_id
  role       = "roles/bigquery.dataEditor"
  member     = google_service_account.orchestrator.member
}