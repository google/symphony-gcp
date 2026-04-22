#!/usr/bin/env bash
# Purpose: Validate that applying a resource request results in creating pods and are ready to use
# Run from k8s-operator/tests/ci/kind-tests with an isolated Kubernetes context.

set -Eeuo pipefail

RESOURCE_MANIFEST="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/manifests/resource.yaml"
NAMESPACE="gcp-symphony"
RESOURCE_NAME="test-resource"

kubectl apply -f "${RESOURCE_MANIFEST}"

kubectl wait --for=create pod \
    -n "$NAMESPACE" \
    -l "app=$RESOURCE_NAME" \
    --timeout=30s

kubectl wait --for=condition=Ready pod \
    -n "$NAMESPACE" \
    -l "app=$RESOURCE_NAME" \
    --timeout=60s

echo "[PASS] Resource request successfully created and initialized pods."