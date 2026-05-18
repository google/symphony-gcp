#!/usr/bin/env bash
# Purpose: Assert that the gcp-symphony-operator is running.
# Run from k8s-operator/tests/ci/kind-tests with an isolated Kubernetes context.

if ! kubectl wait --for=condition=Available \
    "deployment/$IMAGE" \
    --timeout=60s; then
    echo "[FAIL] $IMAGE isn't running properly."
    echo "- Recent Cluster Error Events:"
    kubectl get events --sort-by='.lastTimestamp' | grep -iE "error|fail|warning" | tail -n 5
    
    exit 1
fi

echo "[PASS] $IMAGE is running."