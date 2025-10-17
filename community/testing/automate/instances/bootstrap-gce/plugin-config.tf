locals {
    # Plugin config paths

    plugin_config_dir = "./gce-plugin-config"
    plugin_config = "${local.plugin_config_dir}/plugin_config.json"
    template_config = "${local.plugin_config_dir}/template_config.json"
    plugin_script_tpl = "${local.plugin_config_dir}/script.sh.tftpl"

}

resource "null_resource" "update-configuration-files" {

    triggers = {
        plugin_config = filesha256(local.plugin_config)
        template_config = filesha256(local.template_config)
        # TODO: Add template variables to triggers
        # templates = var.compute_templates
        plugin_script_tpl = filesha256(local.plugin_script_tpl)
        run_id = local.run_id

    }  
    provisioner "local-exec" {

    environment = {
      CLUSTERADMIN = "egoadmin"
      TARGET_VM = data.google_compute_instance.mgmt_vms[0].name
      ZONE = var.zone
      PVT_KEY = var.private_key_path
      COMMAND = local.CONFIG_VM
    }

    interpreter = ["/bin/bash", "-c"]

    # Requires TARGET_VM, ZONE, CLUSTERADMIN, PVT_KEY
    command = <<EOF
      TARGET_IP=$(gcloud compute instances describe --zone $ZONE $TARGET_VM --format="value(networkInterfaces[0].networkIP)")
      if [[ -z $TARGET_IP ]]; then
        echo "ERROR: $TARGET_VM internal IP not found..."
        return 1
      fi
      TARGET_STATUS=$(gcloud compute instances describe --zone $ZONE $TARGET_VM --format="value(status)")
      if [[ $TARGET_STATUS != "RUNNING" ]]; then
        echo "ERROR: $TARGET_VM status is $TARGET_STATUS, expected RUNNING..."
        return 1
      fi
      HTTPS_PROXY= ssh $CLUSTERADMIN@$TARGET_IP \
      -i $PVT_KEY \
      -o StrictHostKeyChecking=no  \
      -o UserKnownHostsFile=/dev/null \
      -o ServerAliveInterval=30 \
      -o ServerAliveCountMax=5 \
      -o ProxyCommand="gcloud compute start-iap-tunnel $TARGET_VM 22 --zone $ZONE --listen-on-stdin" \
      -- <<EOT
$COMMAND
EOT
    EOF
  }
}

locals {
  CONFIG_VM = <<-EOC
    export GCP_GCE_CONF_DIR=$HF_TOP/conf/providers/gcpgceinst
    export GCP_GCE_SCRIPT_DIR=$HF_TOP/$HF_VERSION/providerplugins/gcpgce/scripts
    
    egosh user logon -u Admin -x Admin
    IFS=, read -ra HF_STATUS <<< $(egosh service list -ll | grep HostFactory | tr -d '"' )
    HF_STATUS=$${HF_STATUS[6]}

    if [[ $HF_STATUS -eq "STARTED" ]]; then
      echo "Stopping HostFactory..."
      egosh service stop HostFactory
      sleep 1
    fi
    
    echo "Upgrading plugin config file..."
    mkdir -p $GCP_GCE_CONF_DIR
    cat <<EOF > $GCP_GCE_CONF_DIR/gcpgceinstprov_config.json
    ${templatefile(local.plugin_config, {
      GCP_PROJECT_ID=var.project_id,
      PUBSUB_SUBSCRIPTION=google_pubsub_subscription.plugin-pubsub-subscription.name
    })}
    EOF

    echo "Upgrading plugin template config file..."
    cat <<EOF > $GCP_GCE_CONF_DIR/gcpgceinstprov_templates.json
    ${file(local.template_config)}
    EOF

    # TODO: In a production environment the ncpus and other attributes should also be 
    # in the template
    TEMP_FILE=$(mktemp)
    %{ for name, mig in google_compute_instance_group_manager.hf-compute-manager}
    cat $GCP_GCE_CONF_DIR/gcpgceinstprov_templates.json | jq -r --from-file <(cat <<EOF
    .templates +=[{
      "templateId": "${name}",
      "maxNumber": 99999,
      "attributes": {
        "type": [
          "String",
          "X86_64"
        ],
        "ncpus": [
          "Numeric",
          "1"
        ],
        "ncores": [
          "Numeric",
          "1"
        ],
        "nram": [
          "Numeric",
          "1024"
        ]
      },
      "gcp_zone": "${mig.zone}",
      "gcp_instance_group": "${mig.name}"
    }]
    EOF
    ) > $TEMP_FILE
    cp $TEMP_FILE $GCP_GCE_CONF_DIR/gcpgceinstprov_templates.json
    %{ endfor }

    echo "Upgrading plugin script..."
    cat <<'EOF' > $GCP_GCE_SCRIPT_DIR/script.sh
    ${templatefile(local.plugin_script_tpl, {
      run_id = var.run_id
    })}
    EOF

    echo "Upgrading google-symphony-hf..."
    if python3.12 --version >/dev/null 2>&1; then
      PYTHON_VERSION=python3.12
    else
      echo "⚠️ WARNING: Python 3.12 not found!"
      exit
    fi

    $PYTHON_VERSION \
      -m uv tool install \
      --index=https://oauth2accesstoken:$(gcloud auth print-access-token)@${var.python_repository}/simple google-symphony-hf \
      --upgrade

    echo "Initializing database..."
    export HF_DBDIR=$HF_TOP/db
    export HF_PROVIDER_CONFDIR=$HF_TOP/conf/providers/gcpgceinst
    [[ ! -d $HF_DBDIR ]] && mkdir -p $HF_DBDIR
    [[ ! -f $HF_DBDIR/gcp-symphony ]] && hf-gce initializeDB

    # Start Symphony
    max_attempts=10
    attempt=1
    while true; do
      if ((attempt >= max_attempts)); then
        echo "HostFactory failed to start..."
        break
      fi
      IFS=, read -ra HF_STATUS <<< $(egosh service list -ll | grep HostFactory | tr -d '"' )
      HF_STATUS=$${HF_STATUS[6]}
      if [[ $HF_STATUS -eq "DEFINED" ]]; then
        break
      fi
      sleep 1s
      ((attempt++))
    done

    echo "Starting HostFactory..."
    egosh service start HostFactory
    EOC
}