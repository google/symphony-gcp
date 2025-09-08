#!/bin/bash

# This is a sample script to properly modify the cluster (notably node pool) without losing kuberenetes state managed by terraform
# NOTE: This script is only a **SAMPLE** and has not been tested. 
# It is recommended to run this by hand to check for intermediary errors,
# since error handling is not implemented.

INDEX=0 # Cluster index

PROXY_PORT=6443
TARGET_CLUSTER=cluster-test-${INDEX}
unset HTTPS_PROXY

# ============= Cleanup bootstrap =============

cd $WORKDIR/automate/instances/bootstrap

if [ -z $(ss -tunap | grep $PROXY_PORT) ]; then
    echo "ERROR: Did you forget to open the SSH tunnel?"
    exit 1 
fi

# ==== Make sure we have properly targeted our infrastructure ====

gcloud container clusters get-credentials $TARGET_CLUSTER \
    --location $TF_VAR_region

export HTTPS_PROXY=socks5://127.0.0.1:$PROXY_PORT

if ! kubectl get node --request-timeout=2s ; then
    echo "Hmm... it seems your proxy is not working... Check it! Maybe wrong target VM?"
    exit 1
fi

export TF_WORKSPACE=cluster-${INDEX}

# ==== End target check ====

# Cleanup bootstrap kubernetes state
./cleanup.sh

# ============= Apply modifications to cluster =============

cd $WORKDIR/automate/instances/cluster-base/cluster

# ==== Make sure we have properly targeted our infrastructure ====

unset HTTPS_PROXY

export TF_WORKSPACE=cluster-${INDEX}

gcloud container clusters get-credentials $TARGET_CLUSTER \
    --location $TF_VAR_region

if [ ! -f matrix-samples/test-${INDEX}.json ]; then
echo "matrix-samples/test-${INDEX}.json not found... did you forget to create it?"
    exit 1
fi

# ==== End target check ====

terraform apply -var-file=matrix-samples/test-${INDEX}.json

# ============= Rebootstrap =============

cd $WORKDIR/automate/instances/bootstrap

if [ -z $(ss -tunap | grep $PROXY_PORT) ]; then
    echo "ERROR: Did you forget to open the SSH tunnel?"
    exit 0 
fi

# ==== Make sure we have properly targeted our infrastructure

export HTTPS_PROXY=socks5://127.0.0.1:$PROXY_PORT
gcloud container clusters get-credentials $TARGET_CLUSTER \
    --location $TF_VAR_region
export TF_WORKSPACE=cluster-${INDEX}

if ! kubectl get node --request-timeout=2s ; then
    echo "Hmm... it seems your proxy is not working... Check it! Maybe wrong target VM?"
    exit 1
fi

if [ ! -f matrix-samples/test-${INDEX}.json ]; then
    echo "matrix-samples/test-${INDEX}.json not found... did you forget to create it?"
    exit 1
fi

# ==== End target check ====

terraform apply -var-file=matrix-samples/test-${INDEX}.json
