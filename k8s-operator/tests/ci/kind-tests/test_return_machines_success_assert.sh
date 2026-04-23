#!/usr/bin/env bash
# Purpose: Validate that machine return request completes successfully.
# Run from k8s-operator/tests/ci/kind-tests with an isolated Kubernetes context.

set -Eeuo pipefail

RETURN_RESOURCE_NAME="test-return-request"

sleep 2

MR_PHASE=$(kubectl get mrr "${RETURN_RESOURCE_NAME}" -o jsonpath='{.status.phase}')
MR_RETURNED_MACHINES=$(kubectl get mrr "${RETURN_RESOURCE_NAME}" -o jsonpath='{.status.returnedMachines}')
MR_TOTAL_MACHINES=$(kubectl get mrr "${RETURN_RESOURCE_NAME}" -o jsonpath='{.status.totalMachines}')

if [[ $MR_PHASE != "Completed" || $MR_RETURNED_MACHINES != $MR_TOTAL_MACHINES ]]; then
    echo "[FAIL] Machine return incomplete:"
    echo " - Phase:             $MR_PHASE"
    echo " - Returned machines: $MR_RETURNED_MACHINES"
    echo " - Total machines:    $MR_TOTAL_MACHINES"
    exit 1
fi

echo "[PASS] Machine return request completed successfully."