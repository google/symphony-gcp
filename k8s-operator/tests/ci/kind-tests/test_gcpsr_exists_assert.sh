#!/usr/bin/env bash
# Purpose: Assert that the GCP Symphony Resource (gcpsr) CRD exists in the cluster.
# Run from k8s-operator/tests/ci/kind-tests with an isolated Kubernetes context.
set -Eeuo pipefail

kubectl get crd gcp-symphony-resources.accenture.com -o jsonpath='{.metadata.name}' || { echo "gcpsr CRD not found"; exit 1; }