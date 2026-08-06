#!/usr/bin/env bash
# Purpose: Validate that after a partial MachineReturnRequest removes only 1 pod, the GCPSymphonyResource remains active until the remaining pods are returned and transitions to WaitingCleanup phase.
# Run from k8s-operator/tests/ci/kind-tests with an isolated Kubernetes context.
set -Eeuo pipefail

SLEEP=1
RESOURCE_NAME="test-gcpsr-partial-return-assert"

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
  machineCount: 3
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

# First partial machine return request by returning 1/3 running pods
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

kubectl wait --for=delete pod/$RESOURCE_NAME-pod-0 --timeout=60s

sleep $SLEEP

MR_PHASE=$(kubectl get mrr "${RESOURCE_NAME}-return" -o jsonpath='{.status.phase}')
MR_RETURNED_MACHINES=$(kubectl get mrr "${RESOURCE_NAME}-return" -o jsonpath='{.status.returnedMachines}')

if [[ $MR_RETURNED_MACHINES == 1 && $MR_PHASE == "Completed" ]]; then
  echo "[PASS] First machine return request completed successfully."
else
  echo "[FAIL] First machine return request incomplete:"
  echo " - Phase:             ${MR_PHASE}"
  echo " - Returned machines: ${MR_RETURNED_MACHINES}"
  exit 1
fi

sleep $SLEEP

SR_PHASE=$(kubectl get gcpsr "${RESOURCE_NAME}" -o jsonpath='{.status.phase}')
SR_MACHINE_COUNT=$(kubectl get gcpsr "${RESOURCE_NAME}" -o jsonpath='{.spec.machineCount}')
SR_AVAILABLE_MACHINES=$(kubectl get gcpsr "${RESOURCE_NAME}" -o jsonpath='{.status.availableMachines}')
POD_COUNT=$(kubectl get pods -l "app=${RESOURCE_NAME}" --no-headers | wc -l)

if [[ 
  $SR_MACHINE_COUNT == 3 && \
  $SR_AVAILABLE_MACHINES == 2 && \
  $SR_AVAILABLE_MACHINES == $POD_COUNT && \
  $SR_PHASE == "Running"
]]; then
  echo "[PASS] gcpsr is consistent after first machine return request."
else
  echo "[FAIL] Resources mismatch  after first machine return request:"
  echo " - Requested machines: $SR_MACHINE_COUNT"
  echo " - Available machines: $SR_AVAILABLE_MACHINES"
  echo " - Running pods:       $POD_COUNT"
  exit 1
fi

# Second partial machine return request by returning 2/3 remaining pods
RETURN_RESOURCE="
apiVersion: accenture.com/v1
kind: MachineReturnRequest
metadata:
  name: ${RESOURCE_NAME}-2-return
  namespace: gcp-symphony
spec:
  requestId: ${RESOURCE_NAME}-2-return-request-id
  machineIds:
  - "${RESOURCE_NAME}-pod-1"
  - "${RESOURCE_NAME}-pod-2"
"
kubectl apply -f - <<< "$RETURN_RESOURCE"

kubectl wait --for=delete pod \
  -l "app=$RESOURCE_NAME" \
  --timeout=60s

sleep $SLEEP

MR_PHASE=$(kubectl get mrr "${RESOURCE_NAME}-2-return" -o jsonpath='{.status.phase}')
MR_RETURNED_MACHINES=$(kubectl get mrr "${RESOURCE_NAME}-2-return" -o jsonpath='{.status.returnedMachines}')
MR_TOTAL_MACHINES=$(kubectl get mrr "${RESOURCE_NAME}-2-return" -o jsonpath='{.status.totalMachines}')

if [[  $MR_PHASE == "Completed" && $MR_RETURNED_MACHINES == $MR_TOTAL_MACHINES ]]; then
  echo "[PASS] Second machine return request completed successfully."
else
  echo "[FAIL] Second machine return request incomplete:"
  echo " - Phase:             ${MR_PHASE}"
  echo " - Returned machines: ${MR_RETURNED_MACHINES}"
  echo " - Total machines:    ${MR_TOTAL_MACHINES}"
  exit 1
fi

sleep $SLEEP

SR_MACHINE_COUNT=$(kubectl get gcpsr "${RESOURCE_NAME}" -o jsonpath='{.spec.machineCount}')
SR_AVAILABLE_MACHINES=$(kubectl get gcpsr "${RESOURCE_NAME}" -o jsonpath='{.status.availableMachines}')
POD_COUNT=$(kubectl get pods -l "app=${RESOURCE_NAME}" --no-headers | wc -l)

if [[ 
  $SR_MACHINE_COUNT == 3 && \
  $SR_AVAILABLE_MACHINES == 0 && \
  $SR_AVAILABLE_MACHINES == $POD_COUNT \
]]; then
  echo "[PASS] gcpsr is consistent after second machine return request."
else
  echo "[FAIL] Resources mismatch after second machine return request:"
  echo " - Requested machines: $SR_MACHINE_COUNT"
  echo " - Available machines: $SR_AVAILABLE_MACHINES"
  echo " - Running pods:       $POD_COUNT"
  exit 1
fi

SR_PHASE=$(kubectl get gcpsr "${RESOURCE_NAME}" -o jsonpath='{.status.phase}')

if [ "$SR_PHASE" == "WaitingCleanup" ]; then
  echo "[PASS] Resource is in WaitingCleanup phase and ready for cleanup."
else
  echo "[FAIL] Resource state did not meet the requirement for cleanup."
  echo "- Phase: $SR_PHASE"
  exit 1
fi