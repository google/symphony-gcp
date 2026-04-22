#!/usr/bin/env bash
# Purpose: Validate that returning machines triggers pod termination
# Run from k8s-operator/tests/ci/kind-tests with an isolated Kubernetes context.

set -Eeuo pipefail

RETURN_RESOURCE_MANIFEST="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/manifests/return-resource.yaml"
NAMESPACE="gcp-symphony"
RESOURCE_NAME="test-resource"

kubectl apply -f "${RETURN_RESOURCE_MANIFEST}"

kubectl wait --for=delete pod \
    -n "$NAMESPACE" \
    -l "app=$RESOURCE_NAME" \
    --timeout=60s

echo "[PASS] All pods successfully terminated after return request."