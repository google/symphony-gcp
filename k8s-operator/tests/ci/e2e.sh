#!/usr/bin/env bash
# =========================================
# Script Name: e2e.sh
# Description: End to end script for local kind based testing; basically 
# * It creates a kind cluster if it doesn't exists (it assume you have installed and running kind container)
# - to verify if kind installation is working, you can run `kind version` and `kind get clusters`
# - to rerun the kind container run `docker ps -a` and `docker start <container_id>` with the correct 
# - container id for the kind cluster.
# * It loads the operator image into the cluster
# * It set current namespace 
# * If old cluster exists, it reset the cluster by deleting all deployments, crds and pods.
# * It loads the docker image into the cluster (it assume you have built the operator image and tagged it as 
# - `$OPERATOR_NAME:latest`)
# - It applies the manifests with the correct image reference (it assume that you have exported `manifests.yaml` 
# - in the same directory as this script)
# * It set operator env vars for testing and restarts the operator deployment to apply changes.
# * It runs the test script `run-kind-tests.sh`
# Author: Jheno Cerbito
# Date: 2026-05-11
# =========================================

CLUSTER_NAME="symphony-kind-ci"
OPERATOR_NAME="gcp-symphony-operator"
NAMESPACE="gcp-symphony"
OPERATOR_REGISTRY="localhost/$OPERATOR_NAME:latest"
CONTEXT="kind-$CLUSTER_NAME"

# Operator Environment Variables
GCP_HF_CRD_COMPLETED_RETAIN_TIME=2
GCP_HF_CRD_COMPLETED_CHECK_INTERVAL=1

is_new_cluster=false

# Export variables for use in other scripts
export IMAGE="$OPERATOR_NAME"

echo "creating kind cluster"

if kind get clusters | grep -q "$CLUSTER_NAME"; then
    echo "kind cluster $CLUSTER_NAME already exists, skipping creation"
else
    kind create cluster --name "$CLUSTER_NAME" --wait 60s
    is_new_cluster=true
fi

kubectl config use-context "$CONTEXT"

echo "load docker image into kind cluster"
echo "set namespace to $NAMESPACE"

kubectl config set-context --current --namespace=$NAMESPACE

if [ "${is_new_cluster}" == "false" ]; then
    echo "resetting cluster resources..."

    # delete deployments 
    kubectl delete deployment --all -A --ignore-not-found=true
    # delete gcpsr and mrr resources
    kubectl delete gcpsr --all -A --ignore-not-found=true
    kubectl delete mrr --all -A --ignore-not-found=true
    
    echo "deleting pods only with prefix 'test-'..."
    kubectl get pods -A --no-headers | awk '$2 ~ /^test-/ {print $1, $2}' | while read -r ns pod; do
        kubectl delete pod "${pod}" -n "${ns}" \
        --wait=false \
        --ignore-not-found=true
    done
fi

echo "loading operator image into kind cluster"

kind load docker-image $OPERATOR_REGISTRY --name "$CLUSTER_NAME"

echo "modifying manifests"

sed "s|image: $OPERATOR_NAME:.*|image: $OPERATOR_REGISTRY|" manifests.yaml \
    | kubectl apply -f -

echo "set operator env vars for testing"
kubectl set env deploy/$OPERATOR_NAME \
    GCP_HF_CRD_COMPLETED_RETAIN_TIME=$GCP_HF_CRD_COMPLETED_RETAIN_TIME \
    GCP_HF_CRD_COMPLETED_CHECK_INTERVAL=$GCP_HF_CRD_COMPLETED_CHECK_INTERVAL 

kubectl rollout restart deploy/$OPERATOR_NAME
kubectl rollout status deploy/$OPERATOR_NAME

echo "running script"

bash ./run-kind-tests.sh
