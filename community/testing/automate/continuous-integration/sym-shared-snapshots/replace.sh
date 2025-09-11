#!/bin/bash

terraform apply -auto-approve \
    -replace null_resource.startup_finished \
    -replace google_compute_snapshot.nfs_snapshot \
    -replace google_compute_image.nfs_image \
    -replace google_compute_image.mgmt_image \
    -replace google_compute_image.compute_image