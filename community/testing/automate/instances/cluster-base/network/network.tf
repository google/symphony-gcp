locals {
  network_name = "network-${local.module_suffix}"
}



module "network" {
  source  = "terraform-google-modules/network/google"
  version = "11.0.0"

  network_name = local.network_name
  project_id   = var.project_id
  subnets      = local.subnet_array

  secondary_ranges = local.secondary_ranges

  ingress_rules = [
    {
      name               = "allow-iap-${local.module_suffix}"
      source_ranges      = ["35.235.240.0/20"]
      destination_ranges = ["0.0.0.0/0"]
      allow = [
        {
          protocol = "tcp"
          ports    = ["22"]
        }
      ]
    },
    {
      name               = "allow-internal-${local.module_suffix}"
      source_ranges      = local.all_private_ranges
      destination_ranges = local.all_private_ranges
      allow = [
        {
          protocol = "tcp"
          ports    = ["0-65535"]
        },
        {
          protocol = "udp"
          ports    = ["0-65535"]
        },
        {
          protocol = "icmp"
        },
      ]
    }
  ]

  egress_rules = [
    {
      name         = "allow-egress-all-${local.module_suffix}"
      source_range = "0.0.0.0/0"
      allow = [
        {
          protocol = "tcp"
          ports    = ["0-65535"]
        },
        {
          protocol = "udp"
          ports    = ["0-65535"]
        },
        {
          protocol = "icmp"
        },
      ]
    }
  ]
}

resource "google_compute_router" "nat_router" {
  name    = "nat-router-${local.module_suffix}"
  region  = var.region
  network = module.network.network_id
}

resource "google_compute_router_nat" "nat_gateway" {
  name   = "nat-gateway-${local.module_suffix}"
  router = google_compute_router.nat_router.name
  region = google_compute_router.nat_router.region

  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}
