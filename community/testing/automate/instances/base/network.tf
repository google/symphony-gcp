locals {
  network_name = "symphony-network-${var.module_suffix}"
  subnet_name  = "symphony-subnet-${var.module_suffix}"
}

module "network" {
  source  = "terraform-google-modules/network/google"
  version = "11.0.0"

  network_name = local.network_name
  project_id   = var.project_id
  subnets = [
    {
      subnet_name   = local.subnet_name
      subnet_ip     = var.subnet_ip_cidr_range
      subnet_region = var.region
      subnet_private_access = true
    }
  ]

  firewall_rules = [
    {
      name   = "allow-iap-${var.module_suffix}"
      ranges = ["35.235.240.0/20"]
      allow = [
        {
          protocol = "tcp"
          ports    = ["22"]
        }
      ]
    },
    {
      name   = "allow-internal-${var.module_suffix}"
      ranges = [var.subnet_ip_cidr_range]
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
  name    = "nat-router-${var.module_suffix}"
  region  = var.region
  network = module.network.network_id
}

resource "google_compute_router_nat" "nat_gateway" {
  name   = "nat-gateway-${var.module_suffix}"
  router = google_compute_router.nat_router.name
  region = google_compute_router.nat_router.region

  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}