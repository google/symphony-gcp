#!/usr/bin/env bash
# Purpose: Wait for required CRDs (gcpsr and mrr) to be established before running tests.
# Run from k8s-operator/tests/ci/kind-tests with an isolated Kubernetes context.
set -Eeuo pipefail

kubectl wait --for=condition=Established \
    crd/gcp-symphony-resources.accenture.com \
    --timeout=60s
    
kubectl wait --for=condition=Established \
    crd/machine-return-requests.accenture.com \
    --timeout=60s