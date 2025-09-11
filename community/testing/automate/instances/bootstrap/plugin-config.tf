# TODO: https://github.com/aneoconsulting/terraform-provider-generic/blob/main/tf-test/main.tf

locals {
  # Operator
  operator-configmap-name = "operator-config"
  operator-patch-dir = "${local.plugin_config_dir}/operator-patch"
  operator-kustomization = "${local.operator-patch-dir}/kustomization.yaml"
  operator-patch = "${local.operator-patch-dir}/operator-patch.yaml"
  operator-proxy-patch = "${local.operator-patch-dir}/operator-proxy-patch.yaml"
  operator-priority = "${local.operator-patch-dir}/operator-priority.yaml"
  operator-pdb = "${local.operator-patch-dir}/operator-pdb.yaml"

  # GKE Plugin
  plugin_config_dir = "./gke-plugin-config"
  plugin_config = "${local.plugin_config_dir}/plugin_config.json"
  template_config = "${local.plugin_config_dir}/template_config.json"
  templates_dir = "${local.plugin_config_dir}/templates"
  plugin_script_tpl = "${local.plugin_config_dir}/script.sh.tftpl"
  ops_agent_config = "${local.observability_dir}/ops-agent/ops_agent_config.yaml.tftpl"
  template_fileset = [
    for filename in fileset(local.templates_dir, "**") : "${filename}"
  ]
  templates = [
    for filename in local.template_fileset : "${local.templates_dir}/${filename}"
  ]

  resource_watcher_dir = "${local.observability_dir}/resources"
  resource_script = "${local.resource_watcher_dir}/resource-watcher.sh"
  resource_service = "${local.resource_watcher_dir}/resource-watcher.service"

  # SymA
  syma_config_dir = "./symA"
  syma_config = "${local.syma_config_dir}/symAreq_config.json"
  syma_policy = "${local.syma_config_dir}/symAreq_policy_config.json"
  syma_script_demand = "${local.syma_config_dir}/scripts/getDemandRequests.sh.tftpl"
  syma_script_return = "${local.syma_config_dir}/scripts/getReturnRequests.sh.tftpl"
}

resource "null_resource" "update-configuration-files" {
    depends_on = [ kubernetes_job.bootstrap-hostfactory-operator ]

    triggers = {
        plugin_config = filesha256(local.plugin_config)
        template_config = filesha256(local.template_config)
        templates = join("", [for filename in local.templates : filesha256(filename)])
        script = filesha256(local.plugin_script_tpl)
        ops_agent_config = filesha256(local.ops_agent_config)
        docker_registry = var.docker_repository
        compute_class = data.terraform_remote_state.cluster_output.outputs.compute_class
        logs_ingestor_ip = data.terraform_remote_state.orchestrator-bootstrap.outputs.bg_svc_ip
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
    export GCP_GKE_CONF_DIR=$HF_TOP/conf/providers/gcpgkeinst
    export GCP_GKE_SCRIPT_DIR=$HF_TOP/$HF_VERSION/providerplugins/gcpgke/scripts
    export SYMA_CONFIG_DIR=$HF_TOP/conf/requestors/symAinst
    export SYMA_SCRIPTS_DIR=$HF_TOP/$HF_VERSION/requestorplugins/symA/scripts
    export HF_REQUESTORS=$HF_TOP/conf/requestors/hostRequestors.json
    export CLUSTERADMIN=egoadmin

    export PROJECT_ID=${var.project_id}

    egosh user logon -u Admin -x Admin
    IFS=, read -ra HF_STATUS <<< $(egosh service list -ll | grep HostFactory | tr -d '"' )
    HF_STATUS=$${HF_STATUS[6]}

    if [[ $HF_STATUS -eq "STARTED" ]]; then
      echo "Stopping HostFactory..."
      egosh service stop HostFactory
      sleep 1
    fi

    echo "Getting cluster credentials..."
    gcloud container clusters get-credentials ${local.cluster_name} \
      --location ${local.cluster_location}

    echo "Upgrading plugin config file..."
    cat <<EOF > $GCP_GKE_CONF_DIR/gcpgkeinstprov_config.json
    ${file(local.plugin_config)}
    EOF

    echo "Upgrading plugin template config file..."
    cat <<EOF > $GCP_GKE_CONF_DIR/gcpgkeinstprov_templates.json
    ${file(local.template_config)}
    EOF

    echo "Upgrading plugin templates..."
    %{ for filename, filepath in zipmap(local.template_fileset, local.templates) }
    echo "Upgrading template ${filename}..."
    cat <<EOF >$GCP_GKE_CONF_DIR/pod-specs/${trimsuffix("${filename}",".tftpl")}
    ${templatefile("${filepath}", {
      docker_registry=var.docker_repository
      compute_class=data.terraform_remote_state.cluster_output.outputs.compute_class
    })}
    EOF
    %{ endfor }

    echo "Upgrading plugin script..."
    cat <<'EOF' > $GCP_GKE_SCRIPT_DIR/script.sh
    ${templatefile(local.plugin_script_tpl, {
      logs_ingestor_ip = data.terraform_remote_state.orchestrator-bootstrap.outputs.bg_svc_ip
      run_id = var.run_id
      cluster = local.cluster_name
    })}
    EOF

    echo "Upgrading symA config..."
    cat <<EOF > $SYMA_CONFIG_DIR/symAinstreq_config.json
    ${file(local.syma_config)}
    EOF

    echo "Upgrading symA policy..."
    cat <<EOF > $SYMA_CONFIG_DIR/symAinstreq_policy_config.json
    ${file(local.syma_policy)}
    EOF

    echo "Upgrading symA getDemandRequests.sh..."
    cat <<'EOF' > $SYMA_SCRIPTS_DIR/getDemandRequests.sh
    ${templatefile(local.syma_script_demand, {
      logs_ingestor_ip = data.terraform_remote_state.orchestrator-bootstrap.outputs.bg_svc_ip
    })}
    EOF

    echo "Upgrading symA getReturnRequests.sh..."
    cat <<'EOF' > $SYMA_SCRIPTS_DIR/getReturnRequests.sh
    ${templatefile(local.syma_script_return, {
      logs_ingestor_ip = data.terraform_remote_state.orchestrator-bootstrap.outputs.bg_svc_ip
    })}
    EOF

    echo "Disabling symA..."
    TEMP_FILE=$(mktemp)
    cat $HF_REQUESTORS | jq '(.requestors[] | select(.name=="symAinst") | .enabled) = 0' > $TEMP_FILE
    mv $TEMP_FILE $HF_REQUESTORS

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

    echo "Installing/Configuring Google Cloud Ops Agent"
    OPS_CONFIG=/etc/google-cloud-ops-agent/config.yaml
    if ! sudo systemctl status google-cloud-ops-agent >/dev/null 2>&1; then
    echo "Installing Google Cloud Ops Agent..."
    curl -sSO https://dl.google.com/cloudagents/add-google-cloud-ops-agent-repo.sh
    sudo bash add-google-cloud-ops-agent-repo.sh --also-install
    echo "Google Cloud Ops Agent installed successfully"
    fi
    if [[ ! -d $(dirname $OPS_CONFIG) ]]; then
      sudo mkdir -p $(dirname $OPS_CONFIG)
    fi
    cat<< EOT | sudo tee $OPS_CONFIG >/dev/null 2>&1
    ${templatefile(
      local.ops_agent_config,
      {run_id=local.run_id}
    )}
    EOT

    if [[ $(sudo systemctl status google-cloud-ops-agent 2>/dev/null 1>&2; echo $? ) -eq 0 ]]; then

      sudo systemctl restart google-cloud-ops-agent
    else
      echo "⚠️ WARNING: CloudOps agent not found!"
    fi

    echo "Configuring resource watcher service"
    WATCHER_SCRIPT=/usr/local/bin/resource-watcher.sh
    WATCHER_SERVICE=/etc/systemd/system/resource-watcher.service
    SYSTEMD_USER_DIR=$(dirname $WATCHER_SERVICE)
    if ! test -f $WATCHER_SCRIPT; then

      cat<<EOT | sudo tee $WATCHER_SCRIPT >/dev/null
    ${file(local.resource_script)}
    EOT

      sudo chmod +x $WATCHER_SCRIPT
      if [ ! -d $SYSTEMD_USER_DIR ]; then
        mkdir -p $SYSTEMD_USER_DIR
      fi

      cat<< EOT | sudo tee $WATCHER_SERVICE >/dev/null
    ${file(local.resource_service)}
    EOT
      sudo systemctl daemon-reload
      sudo systemctl enable resource-watcher.service
      sudo systemctl start resource-watcher.service
    fi

    if ! systemctl is-active --quiet resource-watcher.service; then
      echo "⚠️ WARNING: Resource watcher not active!"
    fi

  EOC
}