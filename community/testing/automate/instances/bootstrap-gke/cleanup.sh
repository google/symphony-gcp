#!/bin/env bash

# We do this in order to migrate the node-pools without leaving untracked ressources in the cluster
# This is because the kubernetes resources are left untracked after migration

NAMESPACE=gcp-symphony

confirm() {
    # call with a prompt string or use a default
    read -r -p "${1:-Are you sure? [y/N]} " response
    case "$response" in
        [yY][eE][sS]|[yY]) 
            true
            ;;
        *)
            false
            ;;
    esac
}

echo "Current active terraform workspace is: $(terraform workspace show)"
echo "Current active kubernetes context is: $(kubectl config current-context)"
echo "Current active namespace is: $(kubectl config view --minify -o jsonpath='{..namespace}')"

confirm || exit 0

# Remove kubernetes states from terraform...

terraform state rm $(terraform state list | grep kubernetes_) 2> /dev/null

# Cleanup all kubernetes resources...

# delete CCC / secondary boot
kubectl delete cc test-cc --ignore-not-found=true
kubectl delete gcpresourceallowlists gke-secondary-boot-disk-allowlist --ignore-not-found=true

# delete nfs 
kubectl delete pvc pvc-nfs -n $NAMESPACE --ignore-not-found=true
kubectl delete pv pv-nfs --ignore-not-found=true

# delete manifest applier
kubectl delete clusterrolebinding manifest-applier-role-binding --ignore-not-found=true
kubectl delete rolebinding manifest-applier-binding -n $NAMESPACE --ignore-not-found=true
kubectl delete sa manifest-applier-sa -n default --ignore-not-found=true

# delete job 
kubectl delete job bootstrap-hostfactory-operator -n default --ignore-not-found=true

# delete all gcpsr and consequently pods
kubectl delete gcpsr --all -n $NAMESPACE --ignore-not-found=true
if ! kubectl wait --for=delete pod \
    -n "$NAMESPACE" \
    -l "managed-by=gcp-symphony-operator" \
    --timeout=300s; then
    echo "ERROR: Failed to delete all pods..." >&2 
    exit 1
fi

# delete ns
kubectl delete ns gcp-symphony --ignore-not-found=true
