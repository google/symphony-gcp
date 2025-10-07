#!/bin/env bash

LOCATION=$(gcloud container clusters describe $WORKCLUSTER --format="value(location)")
POOL=$(gcloud container clusters describe $WORKCLUSTER --format="value(nodePools[0].name)")

terraform import google_container_cluster.test-cluster $LOCATION/$WORKCLUSTER
terraform import google_container_node_pool.test-pool $LOCATION/$WORKCLUSTER/$POOL
terraform import google_compute_firewall.allow_gke_to_gce $TF_VAR_project_id/allow-gke-to-gce-$WORKSPACE