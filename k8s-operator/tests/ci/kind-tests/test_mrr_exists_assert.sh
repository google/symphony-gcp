#!/usr/bin/env bash
# Purpose: Assert that the Machine Return Request (mrr) CRD exists in the cluster.
# Run from k8s-operator/tests/ci/kind-tests with an isolated Kubernetes context.
set -Eeuo pipefail

kubectl get crd machine-return-requests.accenture.com -o jsonpath='{.metadata.name}' || { echo "mrr CRD not found"; exit 1; }