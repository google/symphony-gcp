#!/bin/env bash

if [ -z $VAR_FILE ]; then
    echo "VAR_FILE not specified"
fi

NAMESPACE=gcp-symphony
COMPUTE_CLASS=test-pool

terraform import -var-file=$VAR_FILE kubernetes_namespace.plugin-namespace $NAMESPACE
terraform import -var-file=$VAR_FILE kubernetes_service_account.bootstrap-service-account default/manifest-applier-sa
terraform import -var-file=$VAR_FILE kubernetes_role_binding.bootstrap-role-binding $NAMESPACE/manifest-applier-binding
terraform import -var-file=$VAR_FILE kubernetes_cluster_role_binding.bootstrap-role-binding manifest-applier-role-binding
terraform import -var-file=$VAR_FILE kubernetes_job.bootstrap-hostfactory-operator default/bootstrap-hostfactory-operator
terraform import -var-file=$VAR_FILE kubernetes_persistent_volume.nfs_persistent_volume pv-nfs
terraform import -var-file=$VAR_FILE kubernetes_persistent_volume_claim.nfs_pvc $NAMESPACE/pvc-nfs
terraform import -var-file=$VAR_FILE kubernetes_manifest.compute_class "apiVersion=cloud.google.com/v1,kind=ComputeClass,namespace=default,name=$COMPUTE_CLASS"