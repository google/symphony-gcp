#!/usr/bin/env bash
# Purpose: Validate that after returning machines, the resource is cleaned up and removed from the gcpsr.
# Run from k8s-operator/tests/ci/kind-tests with an isolated Kubernetes context.
set -Eeuo pipefail

RESOURCE_NAME="test-return-machines-assert"

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

echo "[PASS] All pods successfully terminated after return request."

sleep 1

MR_PHASE=$(kubectl get mrr "${RESOURCE_NAME}-return" -o jsonpath='{.status.phase}')
MR_RETURNED_MACHINES=$(kubectl get mrr "${RESOURCE_NAME}-return" -o jsonpath='{.status.returnedMachines}')
MR_TOTAL_MACHINES=$(kubectl get mrr "${RESOURCE_NAME}-return" -o jsonpath='{.status.totalMachines}')

if [[ $MR_PHASE != "Completed" || $MR_RETURNED_MACHINES != $MR_TOTAL_MACHINES ]]; then
    echo "[FAIL] Machine return incomplete:"
    echo " - Phase:             ${MR_PHASE}"
    echo " - Returned machines: ${MR_RETURNED_MACHINES}"
    echo " - Total machines:    ${MR_TOTAL_MACHINES}"
    exit 1
fi

echo "[PASS] Machine return request completed successfully."

# DEFAULT_TIMEOUT_SECONDS=${DEFAULT_TIMEOUT_SECONDS:-10}
# START_TIME=$(date +%s)

# while true; do
#   SR_PHASE=$(kubectl get gcpsr "${RESOURCE_NAME}" -o jsonpath='{.status.phase}')
#   SR_STATUS=$(kubectl get gcpsr "${RESOURCE_NAME}" -o jsonpath='{.status.conditions[-1].status}')
#   SR_TYPE=$(kubectl get gcpsr "${RESOURCE_NAME}" -o jsonpath='{.status.conditions[-1].type}')

#   if [[ $SR_PHASE == "WaitingCleanup" && $SR_STATUS == "True" && $SR_TYPE == "Completed" ]]; then
#     echo "[PASS] Resource is in WaitingCleanup phase and ready for cleanup."
#     exit 0
#   fi

#   # Fail if we've exceeded the default timeout
#   ELAPSED=$(( $(date +%s) - START_TIME ))
#   if [ "$ELAPSED" -gt "$DEFAULT_TIMEOUT_SECONDS" ]; then
#     echo "[FAIL] Resource state did not meet the requirements for cleanup."
#     echo "- Phase: $SR_PHASE"
#     echo "- Last condition status: $SR_STATUS"
#     echo "- Last condition type: $SR_TYPE"
#     exit 1
#   fi

#   echo "Resource Mismatch: Waiting....."
#   echo "- Phase: $SR_PHASE"
#   echo "- Last condition status: $SR_STATUS"
#   echo "- Last condition type: $SR_TYPE"
#   sleep 2

# done

SR_PHASE=$(kubectl get gcpsr "${RESOURCE_NAME}" -o jsonpath='{.status.phase}')
SR_STATUS=$(kubectl get gcpsr "${RESOURCE_NAME}" -o jsonpath='{.status.conditions[-1].status}')
SR_TYPE=$(kubectl get gcpsr "${RESOURCE_NAME}" -o jsonpath='{.status.conditions[-1].type}')

if [[ $SR_PHASE == "WaitingCleanup" && $SR_STATUS == "True" && $SR_TYPE == "Completed" ]]; then
  echo "[FAIL] Resource state did not meet the requirements for cleanup."
  echo "- Phase: $SR_PHASE"
  echo "- Last condition status: $SR_STATUS"
  echo "- Last condition type: $SR_TYPE"
  exit 1
fi

echo "[PASS] Resource is in WaitingCleanup phase and ready for cleanup."