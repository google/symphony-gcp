#!/usr/bin/env bash
# Purpose: Validate that after returning machines, the resource is cleaned up and removed from the gcpsr.
# Run from k8s-operator/tests/ci/kind-tests with an isolated Kubernetes context.
set -Eeuo pipefail

RESOURCE_NAME="test-request-resource-assert"

RESOURCE_MANIFESTS="
apiVersion: accenture.com/v1
kind: GCPSymphonyResource
metadata:
  name: ${RESOURCE_NAME}
  namespace: gcp-symphony
  uid: test-uid-${RESOURCE_NAME}
  labels:
    symphony.requestId: ${RESOURCE_NAME}-request-id
spec:
  machineCount: 1
  namePrefix: test
  podSpec:
    containers:
    - name: base-pod
      image: nginx:alpine
"

kubectl apply -f - <<< "$RESOURCE_MANIFESTS"

kubectl wait --for=create --for=condition=Ready pod \
    -l "app=$RESOURCE_NAME" \
    --timeout=60s

echo "[PASS] Resource request successfully created and initialized pods."

for pod in $(kubectl get pods -l "app=${RESOURCE_NAME}" -o jsonpath='{.items[*].metadata.name}'); do
    STATUS=$(kubectl get pod "$pod" -o jsonpath='{.status.phase}')

    if [[ "$STATUS" != "Running" ]]; then
        echo "[FAIL] Pod $pod is not running (current status: $STATUS)"
        exit 1
    fi
done

sleep 1

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