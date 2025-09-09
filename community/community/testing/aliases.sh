#!/bin/env bash

# === Auxiliary Functions ===

alias k=kubectl
alias tf=terraform
alias tfw="terraform workspace"

essh_generate_config () {
    # $1 is the target VM name.
    local TARGET_VM=$1
    TARGET_IP=$(gcloud compute instances describe "$TARGET_VM" --format="value(networkInterfaces[0].networkIP)")
    [[ -z "$TARGET_IP" ]] && echo "ERROR: IP not found" && return 1
    local TARGET_STATUS
    TARGET_STATUS=$(gcloud compute instances describe "$TARGET_VM" --format="value(status)")
    [[ "$TARGET_STATUS" != "RUNNING" ]] && echo "ERROR: status is $TARGET_STATUS" && return 1
    local SSHCONF=$(mktemp)
    TARGET_ZONE=$(gcloud compute instances list --filter="name=('${TARGET_VM}')" --format="value(zone.basename())")
    cat > "$SSHCONF" <<EOF
Host $TARGET_VM
    HostName $TARGET_IP
    User $CLUSTERADMIN
    IdentityFile $TF_VAR_private_key_path
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    ServerAliveInterval 30
    ServerAliveCountMax 5
    SetEnv TERM=xterm
    ProxyCommand gcloud compute start-iap-tunnel $TARGET_VM 22 --listen-on-stdin --zone $TARGET_ZONE
EOF
    echo $SSHCONF
}

essh () {
    # (e)go ssh...
    # SSH without google interfering...
    # $1 is the target VM name.
    local TARGET_VM=$1
    local ARGS=("${@:2}")
    local SSHCONF=$(essh_generate_config $TARGET_VM)
    echo "Storing temporary config file to $SSHCONF"
    # Disable proxy because it's already proxied...
    HTTPS_PROXY= ssh -F "$SSHCONF" $TARGET_VM "${ARGS[@]}"
    rm "$SSHCONF" 
}

escprl() {
    # (e)go scp remote to local
    # $1 is the target VM name.

    local TARGET_VM=$1
    local REMOTE_PATH=$2
    local LOCAL_PATH=$3
    local SSHCONF=$(essh_generate_config $TARGET_VM)
    echo "Storing temporary config file to $SSHCONF"
    # Use scp with this temporary config
    scp -F "$SSHCONF" "$TARGET_VM:$REMOTE_PATH" "$LOCAL_PATH"
    rm "$SSHCONF"
}

ecred () {
    # Set the credentials on the remote management node
    # $1 is the target VM name.
    local TARGET_VM=$1
    essh $TARGET_VM -- gcloud container clusters get-credentials $WORKCLUSTER \
        --zone $TF_VAR_zone \
        --project $TF_VAR_project_id
}

esshl () {
    # (e)go ssh...
    # SSH without google interfering...
    # $1 is the target VM name.
    local TARGET_VM=$1 
    local REMOTE_PORT=$2
    local LOCAL_PORT=$3
    local ARGS=("${@:4}")
    if [[ -z $LOCAL_PORT ]]; then
      LOCAL_PORT=$REMOTE_PORT
    fi
    
    essh $TARGET_VM -L $REMOTE_PORT:127.0.0.1:$REMOTE_PORT -Nvvv "${ARGS[@]}"
}

esshd () {
    # (e)go ssh...
    # SSH without google interfering...
    # $1 is the target VM name.
    local TARGET_VM=$1 
    local REMOTE_PORT=$2
    local ARGS=("${@:3}")
    
    essh $TARGET_VM -D $REMOTE_PORT -Nvvv "${ARGS[@]}"
}

gcred () {
  # get container credentials
  # $1 is target cluster.
  gcloud container clusters get-credentials $1 \
    --location $TF_VAR_region
}

# TODO: Fix this...
# escp () {
#     # (e)go ssh...
#     # SSH without google interfering...
#     # $1 is the target VM name.
#     local args=("$@")
#     TARGET_IP=$(gcloud compute instances describe "${args[1]}" --format="value(networkInterfaces.accessConfigs[0].natIP)")
#     scp $CLUSTERADMIN@$TARGET_IP -i $PVT_KEY -o StrictHostKeyChecking=no  -o UserKnownHostsFile=/dev/null "${args[@]:1}"
# }

gtags () {
    # (g)oogle tags...
    # Get tags from a VM...    
    # $1 is the target VM name.
    gcloud compute instances describe $1 --format="value(tags.items)"
}

mergekube () {
    KUBECONFIG="$1:$2" kubectl config view --flatten > $3
}

# ============ AUTOMATION ============

tf_shrd_restored () {
  # $1 is the terraform verb (plan, apply...) 
  # $2 is the target restored CI workspace
  # ${2:@} is any extra arguments for terraform plan

  # DO NOT FORGET TO PREVIOUSLY SELECT CORRECT WORKSPACE!

  local SHARED_RESTORED_DIR=$WORKDIR/automate/instances/sym-shared-restored
  local MATRIX_DIR=$WORKDIR/automate/instances/sym-shared/matrix
  local TERRAFORM_VERB=$1
  local TARGET_WORKSPACE=$2
  local ARGS=("${@:3}")


  if [[ -z $TARGET_WORKSPACE ]]; then
      echo "Target matrix configuration not informed, please specify a argument..."
      return 1
  fi

  local MATRIX_CONF=$MATRIX_DIR/$TARGET_WORKSPACE.json

  if [[ ! -f $MATRIX_CONF ]]; then
      echo "Target matrix configuration file ($MATRIX_CONF) not found, please check target config..."
      return 1
  fi

  echo "$TERRAFORM_VERB of $TARGET_WORKSPACE CI snapshot..."

  terraform -chdir=$SHARED_RESTORED_DIR $TERRAFORM_VERB -var-file=$MATRIX_CONF -var "ci-workspace=${TARGET_WORKSPACE}" "${ARGS[@]}"
}

# ============ GOOGLE CLOUD ============

gssh () {
  local TARGET_VM=$1
  local ARGS=("${@:2}")
  TARGET_ZONE=$(gcloud compute instances list --filter="name=('${TARGET_VM}')" --format="value(zone.basename())")
  echo "Target zone is: $TARGET_ZONE"
  gcloud compute ssh $TARGET_VM --zone="${TARGET_ZONE}" --tunnel-through-iap "${ARGS[@]}"
}

gsshd () {
  local TARGET_VM=$1
  local TARGET_PORT=$2
  local ARGS=("${@:3}")
  gssh $TARGET_VM -- -D "$TARGET_PORT" -Nvvv "${ARGS[@]}"
}

gscp () {
  gcloud compute scp $@
}

ginst () {
  gcloud compute instances list 
}

gsshl () {
  gcloud compute ssh $1 -- -L $2:127.0.0.1:$2 -N -vvv
}