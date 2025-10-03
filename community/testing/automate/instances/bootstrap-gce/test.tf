resource "random_id" "run_id" {
    count = var.run_id == null ? 1 : 0
    byte_length = 8
}

locals {
    run_id = var.run_id == null ? random_id.run_id[0].id : var.run_id
}