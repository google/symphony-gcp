# TODO: Output all network module and service account...

output "subnet" {
  value = module.network.subnets["${var.region}/${local.subnet_name}"]
}

output "network" {
  value = module.network
}

output "service_account" {
  value = google_service_account.egoadmin-sa
}