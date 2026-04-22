#!/usr/bin/env bash
# Purpose: Verify that symphony resource enters the WaitingCleanup phase after machine return.
# Run from k8s-operator/tests/ci/kind-tests with an isolated Kubernetes context.

set -Eeuo pipefail

NAMESPACE="gcp-symphony"
RESOURCE_NAME="test-resource"

SR_PHASE=$(kubectl get gcpsr "${RESOURCE_NAME}" -n "${NAMESPACE}" -o jsonpath='{.status.phase}')
SR_STATUS=$(kubectl get gcpsr "${RESOURCE_NAME}" -n "${NAMESPACE}" -o jsonpath='{.status.conditions[-1].status}')
SR_TYPE=$(kubectl get gcpsr "${RESOURCE_NAME}" -n "${NAMESPACE}" -o jsonpath='{.status.conditions[-1].type}')

if [[ $SR_PHASE != "WaitingCleanup" || $SR_STATUS != "True" || $SR_TYPE != "Completed" ]]; then
    echo "[FAIL] Resource state did not meet the requirements for cleanup."
    echo "- Phase: $SR_PHASE"
    echo "- Last condition status: $SR_STATUS"
    echo "- Last condition type: $SR_TYPE"
    exit 1
fi

echo "[PASS] Resource is in WaitingCleanup phase and ready for cleanup."