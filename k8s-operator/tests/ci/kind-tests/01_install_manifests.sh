#!/usr/bin/env bash
# Purpose: Apply operator manifests used by CI tests (manifests.yaml).
# Run from k8s-operator/tests/ci/kind-tests with an isolated Kubernetes context.
set -Eeuo pipefail

kubectl apply -f manifests.yaml