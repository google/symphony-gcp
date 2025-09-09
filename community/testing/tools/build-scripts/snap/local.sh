#!/bin/env bash

set -e

if [ -z $WORKDIR ]; then
    echo "WORKDIR variable is not set" 1>&2
    exit 1
fi

if [ -z $TF_VAR_state_bucket ]; then
    echo "TF_VAR_state_bucket variable is not set" 1>&2
    exit 1
fi

if [ -z $TARGET_MATRIX ]; then
    echo "TARGET_MATRIX variable is not set" 1>&2
    exit 1
fi

SYM_LOCAL_DIR=$WORKDIR/automate/instances/sym-local
TARGET_MATRIX_PATH=$SYM_LOCAL_DIR/matrix/$TARGET_MATRIX.json

if ! test -f $TARGET_MATRIX_PATH; then
    echo "$TARGET_MATRIX file not found..." 1>&2
fi

CI_LOCAL_DIR=$WORKDIR/automate/continuous-integration/sym-local-snapshots

# Apply main project
cd $SYM_LOCAL_DIR
terraform init -backend-config="bucket=${TF_VAR_state_bucket}"
export TF_WORKSPACE=$TARGET_MATRIX
terraform workspace new $TARGET_MATRIX || true
terraform validate
PLAN_FILE=$(mktemp)
terraform plan -var-file=$TARGET_MATRIX_PATH -var=install_only=true -out=$PLAN_FILE;
terraform apply $PLAN_FILE

# Apply snapshot
cd $CI_LOCAL_DIR
terraform init -backend-config="bucket=${TF_VAR_state_bucket}"
terraform workspace new $TARGET_MATRIX || true
terraform validate
PLAN_FILE=$(mktemp)
terraform plan -out=$PLAN_FILE \
	-replace null_resource.startup_finished \
	-replace google_compute_image.mgmt_image \
	-replace google_compute_image.compute_image; \
terraform apply $PLAN_FILE
	
# Destroy main project
cd $SYM_SHARED_DIR
PLAN_FILE=$(mktemp)
terraform plan -destroy -var-file=$TARGET_MATRIX_PATH -out=$PLAN_FILE
terraform apply $PLAN_FILE)