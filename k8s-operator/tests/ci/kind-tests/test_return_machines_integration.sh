#!/usr/bin/env bash
# Purpose:
# Run from k8s-operator/tests/ci/kind-tests with an isolated Kubernetes context.

set -Eeuo pipefail

RETURN_RESOURCE_MANIFEST="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/manifests/return-resource.yaml"
NAMESPACE="gcp-symphony"
LABEL="app=test-resource-5"

kubectl apply -f "${RETURN_RESOURCE_MANIFEST}"

kubectl wait --for=delete pod\
    -n "$NAMESPACE" \
    -l "$LABEL" \
    --timeout=60s

echo "All pods are deleted."