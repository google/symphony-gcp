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
DEFAULT_TIMEOUT_MINUTES=5
DEFAULT_TIMEOUT_SECONDS=$((DEFAULT_TIMEOUT_MINUTES *  60))
STALL_TIMEOUT_MINUTES=4 # stall timeout must be > GCP_HF_CRD_COMPLETED_RETAIN_TIME
STALL_TIMEOUT_SECONDS=$((STALL_TIMEOUT_MINUTES * 60))
START_TIME=$(date +%s)

while true; do
  # Check if resource still exists in gcpsr list
  if ! kubectl get gcpsr --no-headers 2>/dev/null | awk '{print $1}' | grep -qx "${RESOURCE_NAME}"; then
    echo "[PASS] Resource '${RESOURCE_NAME}' is no longer present."
    exit 0
  fi

  ELAPSED=$(( $(date +%s) - START_TIME ))

  if [ "$ELAPSED" -gt "$STALL_TIMEOUT_SECONDS" ]; then
    # This sometimes can happen during node failures or very high control-plane activity where  the completed events get lost to operator
    # Reference Link: https://github.com/google/symphony-gcp/blob/main/k8s-operator/docs/operator-troubleshooting-guide.md#gcpsymphonyresource-in-waitingcleanup-state-for-longer-than-the-crd_completed_retain_time
    echo "Resource '${RESOURCE_NAME}' still exists after ${STALL_TIMEOUT_MINUTES} minutes. This may indicate a stall in cleanup processing."
    echo "Verifying resource manually..."
    # Check for any pods that are associated with this gcpsr using requestId
    PODS=$(kubectl get pods -l symphony.requestId=${RESOURCE_NAME}-request-id -o jsonpath='{.items[*].metadata.name}')
    # Check if the mrr with resource name exists.
    MRR_RESOURCE=$(kubectl get mrr --no-headers 2>/dev/null | awk '{print $1}' | grep -qx "${RESOURCE_NAME}-return" && echo "yes" || echo "no")
    # Check if the gcpsr is still in WaitingCleanup phase
    PHASE=$(kubectl get gcpsr "${RESOURCE_NAME}" -o jsonpath='{.status.phase}')
    # manually deleting the resource to unblock cleanup if they still exist.
    if [[ -z "$PODS" && "$MRR_RESOURCE" == "no" && "$PHASE" == "WaitingCleanup" ]]; then
      echo "Manually deleting resource '${RESOURCE_NAME}' to unblock cleanup..."
      kubectl delete gcpsr "${RESOURCE_NAME}" --ignore-not-found=true
      continue
    else
      echo "Resource '${RESOURCE_NAME}' is still present with the following details:"
      echo " - Associated Pods: ${PODS:-None}"
      echo " - MRR Resource Exists: ${MRR_RESOURCE}"
      echo " - Current Phase: ${PHASE}"
      echo "Manual deletion will not be performed as there are still associated resources or the phase is not WaitingCleanup."
    fi
  fi

  # Fail if we've exceeded the default timeout
  if [ "$ELAPSED" -gt "$DEFAULT_TIMEOUT_SECONDS" ]; then
    echo "[FAIL] Resource '${RESOURCE_NAME}' still exists after ${DEFAULT_TIMEOUT_MINUTES} minutes."
    exit 1
  fi

  sleep 60
done