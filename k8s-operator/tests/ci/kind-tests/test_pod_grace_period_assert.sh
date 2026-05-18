#!/usr/bin/env bash
# Purpose: 
# Run from k8s-operator/tests/ci/kind-tests with an isolated Kubernetes context.
set -Eeuo pipefail

RESOURCE_NAME="test-pod-grace-period-assert"

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

START=$(date +%s)

# wait for pod to enter terminating state...

echo "Waiting for pod to enter terminating state..."

for i in {1..20}; do
    TS=$(kubectl get pod $RESOURCE_NAME -o jsonpath='{.items[0].metadata.deletionTimestamp}' 2>/dev/null || true)
        [ -n "$TS" ] && break
    sleep 1
done

# wait until pod is gone

echo "Waiting for pod to be deleted..."

while kubectl get pod $RESOURCE_NAME >/dev/null 2>&1; do
    sleep 5
done

END=$(date +%s)
ELAPSED=$((END - START))

echo "Elapsed: ${ELAPSED} seconds"

# assertion
if [ "$ELAPSED" -ge 10 ] && [ "$ELAPSED" -le 120 ];
then
    echo "[PASS] Pod entered terminating state and respected the grace period."
    exit 0
fi

echo "[FAIL] Pod did not respect the grace period. Elapsed time: ${ELAPSED} seconds."
exit 1