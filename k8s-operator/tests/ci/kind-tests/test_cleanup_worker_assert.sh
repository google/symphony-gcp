#!/usr/bin/env bash
# Purpose: Validate that after returning machines, the resource is cleaned up and removed from the gcpsr.
# Run from k8s-operator/tests/ci/kind-tests with an isolated Kubernetes context.
set -Eeuo pipefail

RESOURCE_NAME="test-resource-cleanup-worker-assert"

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

kubectl wait --for=create pod \
    -l "app=$RESOURCE_NAME" \
    --timeout=60s

kubectl wait --for=condition=Ready pod \
    -l "app=$RESOURCE_NAME" \
    --timeout=60s

RETURN_RESOURCE="
apiVersion: accenture.com/v1
kind: MachineReturnRequest
metadata:
  name: ${RESOURCE_NAME}-return
  namespace: gcp-symphony
spec:
  requestId: ${RESOURCE_NAME}-return-request-id
  machineIds:
  - "${RESOURCE_NAME}-pod-0"
"

kubectl apply -f - <<< "$RETURN_RESOURCE"

kubectl wait --for=delete pod \
    -l "app=$RESOURCE_NAME" \
    --timeout=60s

# Default timeout (minutes) to wait for resource removal from gcpsr after return request is processed
DEFAULT_TIMEOUT_MINUTES=${DEFAULT_TIMEOUT_MINUTES:-4}
DEFAULT_TIMEOUT_SECONDS=$((DEFAULT_TIMEOUT_MINUTES * 60))
START_TIME=$(date +%s)

while true; do
  # Check if resource still exists in gcpsr list
  if ! kubectl get gcpsr --no-headers 2>/dev/null | awk '{print $1}' | grep -qx "${RESOURCE_NAME}"; then
    echo "[PASS] Resource '${RESOURCE_NAME}' is no longer present."
    exit 0
  fi

  # Fail if we've exceeded the default timeout
  ELAPSED=$(( $(date +%s) - START_TIME ))
  if [ "$ELAPSED" -gt "$DEFAULT_TIMEOUT_SECONDS" ]; then
    echo "[FAIL] Resource '${RESOURCE_NAME}' still exists after ${DEFAULT_TIMEOUT_MINUTES} minutes."
    exit 1
  fi

  sleep 60
done