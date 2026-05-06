#!/usr/bin/env bash
# Purpose: Assert that the gcp-symphony-operator pod is running.
# Run from k8s-operator/tests/ci/kind-tests with an isolated Kubernetes context.

if ! kubectl wait --for=create --for=condition=Ready pod \
    -l "app=$IMAGE" \
    --timeout=60s; then
    REASON=$(kubectl get pods -l app=$IMAGE -o jsonpath='{.items[0].status.containerStatuses[0].state.waiting.reason}')
    MESSAGE=$(kubectl get pods -l app=$IMAGE -o jsonpath='{.items[0].status.containerStatuses[0].state.waiting.message}')
    
    echo "[FAIL] $IMAGE isn't running properly."
    echo " - Likely reason: ${REASON:-Unknown} - ${MESSAGE:-No error message provided.}"

    exit 1
fi

echo "[PASS] $IMAGE is running."