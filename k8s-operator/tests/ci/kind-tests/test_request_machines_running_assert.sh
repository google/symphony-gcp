#!/usr/bin/env bash
# Purpose: Validate that all requested machines are running and the resource state is consistent.
# Run from k8s-operator/tests/ci/kind-tests with an isolated Kubernetes context.

set -Eeuo pipefail

RESOURCE_NAME="test-resource"

for pod in $(kubectl get pods -l "app=${RESOURCE_NAME}" -o jsonpath='{.items[*].metadata.name}'); do
    STATUS=$(kubectl get pod "$pod" -o jsonpath='{.status.phase}')

    if [[ "$STATUS" != "Running" ]]; then
        echo "[FAIL] Pod $pod is not running (current status: $STATUS)"
        exit 1
    fi
done

sleep 2

SR_MACHINE_COUNT=$(kubectl get gcpsr "${RESOURCE_NAME}" -o jsonpath='{.spec.machineCount}')
SR_AVAILABLE_MACHINES=$(kubectl get gcpsr "${RESOURCE_NAME}" -o jsonpath='{.status.availableMachines}')
SR_PHASE=$(kubectl get gcpsr "${RESOURCE_NAME}" -o jsonpath='{.status.phase}')
POD_COUNT=$(kubectl get pods -l "app=${RESOURCE_NAME}" --no-headers | wc -l)

if [[ 
    $SR_MACHINE_COUNT != $SR_AVAILABLE_MACHINES || \
    $SR_AVAILABLE_MACHINES != $POD_COUNT || \
    $SR_PHASE != "Running" 
]] then
    echo "[FAIL] Resources mismatch:"
    echo " - Requested machines: $SR_MACHINE_COUNT"
    echo " - Available machines: $SR_AVAILABLE_MACHINES"
    echo " - Running pods:       $POD_COUNT"
    echo " - Resource phase:     $SR_PHASE"
    exit 1
fi

echo "[PASS] All machines are running and the resource state is consistent."