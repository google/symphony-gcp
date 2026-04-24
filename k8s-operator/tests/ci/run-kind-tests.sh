#!/usr/bin/env bash
set -Eeuo pipefail
# =========================================
# Script Name: run-kind-tests.sh
# Description: Runs all shell test scripts in the adjacent kind-tests directory by
# invoking `bash` on each `*.sh` file; prints progress and fails fast on any error
# (script is executed with `set -Eeuo pipefail`).
# Author: Jheno Cerbito
# Date: 2026-04-10
# =========================================

echo "[INFO] Modifying manifests.yaml to use localhost image registry..."
echo "[INFO] Applying CRD manifests to the cluster..."

sed 's|image: gcp-symphony-operator:.*|image: localhost/gcp-symphony-operator:latest|' manifests.yaml \
| kubectl apply -f -

echo "[INFO] Waiting for CRDs to be established..."

kubectl wait --for=condition=Established \
    crd/gcp-symphony-resources.accenture.com \
    --timeout=60s
    
kubectl wait --for=condition=Established \
    crd/machine-return-requests.accenture.com \
    --timeout=60s

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/kind-tests"

echo "[INFO] Running integration tests from directory: $TEST_DIR"

for test_script in "$TEST_DIR"/*.sh; do
    printf "\n[INFO] Running test script: $test_script\n"
    bash "$test_script"
done

echo
echo "[INFO] All integration tests passed successfully!"