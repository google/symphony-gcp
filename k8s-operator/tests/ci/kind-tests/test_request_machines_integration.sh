#!/usr/bin/env bash
# Purpose:
# Run from k8s-operator/tests/ci/kind-tests with an isolated Kubernetes context.

set -Eeuo pipefail

RESOURCE_MANIFEST="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/manifests/resource.yaml"
NAMESPACE="gcp-symphony"
LABEL="app=test-resource-5"

# kubectl apply -f "${RESOURCE_MANIFEST}"

kubectl wait --for=create pod\
    -n "$NAMESPACE" \
    -l "$LABEL" \
    --timeout=30s

kubectl wait --for=condition=Ready pod\
    -n "$NAMESPACE" \
    -l "$LABEL" \
    --timeout=60s

for pod in $(kubectl get pods -n "${NAMESPACE}" -l "${LABEL}" -o jsonpath='{.items[*].metadata.name}'); do
    STATUS=$(kubectl get pod "$pod" -n "${NAMESPACE}" -o jsonpath='{.status.phase}')

    if [[ "$STATUS" != "Running" ]]; then
        echo "Pod $pod is not running (status: $STATUS)"
        exit 1
    fi
    
    echo "Pod $pod is Running."
done

echo "All pods are running successfully!"