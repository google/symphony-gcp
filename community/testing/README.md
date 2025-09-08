# GCP Symphony Testing

This code contains automation scripts for testing the HostFactory GCP Symphony plugin.
It has the following pourposes:

- Infrastructure: Create the necessary infrastructure around the Symphony in order to use the connector. I.E. the cluster where the compute nodes will be deployed. 
- Installation: Build and push the pluging and install Symphony onto VMs. 
- Bootstraping: Associate the surrounding infrastructure with the Symphony installation.
- Observability: Ingest logs and provide queries to understand the backbone of the pluging workflow. Also provide visualization means.
- Utilities: Provide additional utilities such as a HostFactory Python API wrapper for easier testing. 

## Usage

### Vocabulary

There is overlap in the vocabulary used in this testing project, possibly leading to confusion. In the documentation and commentaries we try to clarify it, but the clarification is not exaustive. Here is a list of the most confusing words and their explanation:

- Project
    - Google project. 
    - Terraform project directory (i.e. contains `.terraform.lock`).
- Cluster
    - Symphony cluster.
    - Kubernetes cluster.
- Node
    - Kubernetes node.
    - Symphony compute / management node (can be pods).


### Summary 

This folder is divided by the following directories:

- `automate`: Contains the core automation scripts, composed mostly of Terraform projects. Contains also the Docker scripts for the compute nodes.
- `bootstrap-project`: Contains base Terraformed infrastructure for building the (Google) project.
- `outils`: Contains general auxiliary tools for either controlling (operating) or observing the infrastructure.

### Variables

Copy and populate the `.env.sample` file to a `.env` file. Source it to avoid being required to inform non-volatile varaibles. 

### Google Project Boostraping

In order to use this testing framework, one needs to initialize basic resources in the Google project. This is done through the `bootstrap-project` directory.

Currently the project bootstraping does not include the required APIs, so these will be required to be enabled manuially.

#### Bucket creation

Create the bucket where the terraform state and Symphony binaires and licenses will be stored by using the `bootstrap-project/bucket` terraform code. The state of this project is stored locally. 

#### Registry creation

Create the registries where we will store the Docker images and Python libraries through the `bootstrap-project/registry` directory. In order to do this, run the following commands and note that these will generally repeat themselves during the project init:

```sh
terraform init -reconfigure -backend-config="bucket=${TF_VAR_state_bucket}"
terraform apply
```

### Base Instances

This terraform project (`automate/instances/base`) was initally developped to use a single subnet on a main VPC. This was later upgraded to support multiple subnets without overlapping IPs to better handle multiple (Symphony and GKE) clusters. Thus, this project contains the legacy VPC which is can still be used for CI / Image building and other functionalities still required by the other terraform projects. It contains the following resources:

- The (Symphony) cluster administrator service account and permissions.
- Some additional roles to the default compute service account.
- The SSH private key secret for the (Symphony) cluster administrator.
- A Cloudops policy for installing the ops agent on Symphony VMs.
- The legacy VPC, subnet, firewall rules, NAT routes and gateway.

> [!IMPORTANT]
> Please note that this project can be used as a base for a production deployment, but for this the service account used needs to be subdivided into many others and their roles reduced considerably.


### Kubernetes Cluster 

These terraform projects (`automate/instances/cluster-base`) were developped in order to create the necessary network configuration and (Kubernetes) cluster configuration for deploying and testing multiple Symphony clusters simultaneously.

#### Kubernetes Cluster Network

The terraform project `automate/instances/cluster-base/network` creates the necessary VPC, subnets, firewall rules and NAT router/gateway for deploying multiple Symphony / GKE clusters. It also creates special "orchestrator" subnets which are able to communicate to all other subnets, for use in testing.

#### Kubernetes Cluster

The terraform project `automate/instances/cluster-base/cluster` allows one to create multiple terraform workspace-based clusters, with a configuration that has been optimized of observability and fast autoscaling. Each workspace will represent a test space/instance. Following is an example script for initialization, where `$WORKSPACE` is a variable containing the desired test space name:

```sh
terraform init -reconfigure -backend-config="bucket=${TF_VAR_state_bucket}"
terraform workspace select -or-create=${WORKSPACE}
terraform apply -var-file=/matrix-samples/test-simple.json
```

Of course, one can customize the (GKE) cluster configuration by modifying the desired terraform variables.

### Symphony Cluster

There are three forms of initializing the Symphony cluster, all of these are done through the Symphony modules at `automate/modules/symphony`.

#### Symphony Binaries

In order to use this automation code, one needs to populate the previously created bucket with the Symphony binaries and licenses. It is recommended to use Symphony version 7.3.2, and in this case is necessary to also populate the bucket with the official Symphony patch 601711. Please note that this version is the best adapted for compatibility with the available GKE kernels.

#### (NFS) Shared Symphony Cluster

The `automate/instances/sym-shared` terraform project allows one to initialize a Symphony cluster from scratch. It uses a custom NFS server to increase speed and allow for the quick-restoring of a shared Symphony cluster for testing pourposes. 

> [!IMPORTANT]
> The usage of this custom NFS server implies some modifications to the startup script, such as disabling OS Login and disabling the Google Guest service which are not recommended for production clusters.

> [!IMPORTANT]
> On a production ready shared Symphony cluster it is recommended to use a managed NFS solution such as Filestore.

Initialize it similarly to as previously stated:

```bash
terraform init -reconfigure -backend-config="bucket=${TF_VAR_state_bucket}"
terraform workspace select -or-create=${WORKSPACE}
terraform apply -var-file=/matrix-samples/test-simple.json
```

Note the following variables in the terraform variable file:

- `network_from`: Specifies wether to use the new or legacy VPC.
- `cluster_index`: Specifies which subnet to use in case of the new VPC. This means that this Symphony deployment will be able to communicate and deploy to the corresponding cluster.

Of course, one can customize the (Symphony) cluster configuration by modifying the desired terraform variables.

#### Local Symphony Cluster

Similar to the NFS Symphony cluster, but does not use a NFS server for failover. Use the same methodology as previously.

### Orchestrator

During the evolution of this project the necessity of an orchestrator appeared, i.e. a VM and/or (Kubernetes) cluster which is able to interact with the many possible (Symphony) clusters and VMs in order to remotely control and observe them. For this we developped the `automate/instances/orchestrator` terraform projects.

The deployments of the orchestrator projets is not strictly necessary for basic testing, although not having it will require some modification of the bootstrap project.


### Bootstrap

The boostrap project is what glues the VM-based Symphony cluster to the GKE cluster. It contains many objects which allow for customizing the plugin configuration and the automatic deployment of the operator and CLI plugin to the concerned instances. It requires targeting the desired Symphony / GKE deployment with the following variables:

- `target_symphony_shared_workspace`: The shared Symphony terraform workspace.
- `target_cluster_workspace`: The target cluster terraform workspace.

The following is a non-exaustive list of what this project does:

- Installs the CLI on the target master Symphony VM.
- Deploys the operator on the target GKE cluster.
    - Additionaly creates a pod disruption budget associated.
    - Additionaly creates a priority class for the pod.
- Creates multiple logging sinks into bigquery for observability.
- Configures the Cloud Ops agent on the Symphony master for ingesting Symphony logs.
- (Disabled) configures the SymA provider on the Symphony master. 
- Creates a compute class on the GKE cluster for hosting the Symphony compute nodes. 
- Enables the usage of secondary boot disks through a `GCPResourceAllowlist` GKE resource. 

#### Images

In order to use this terraform project, one is required to have already built the plugin docker images and python modules. Checkout the `outils/build-scripts/code` directory for guidance on how to do it.

This project also supports the usage of secondary boot disks containing the desired Symphony docker image. See `automate/modules/symphony/docker/local/makefile` for guidance on how to create it.

#### Bootstrap configuration

This terraform project enables the user to configure the files which are used by the Symphony installation to configure the plugin:

- `automate/instances/bootstrap/gke-plugin-config/plugin_config.json` contains the pluging configuration.
- `automate/instances/bootstrap/gke-plugin-config/template_config.json` contains the template configuration.
- `automate/instances/bootstrap/gke-plugin-config/templates` contains all the templates.
- `automate/instances/bootstrap/gke-plugin-config/operator-patch` contains Kustomization patches to be applied to the default operator manifest, as well as additional manifests.
- `automate/instances/bootstrap/observability` contains LQL logging sinks and transforms for ingestion into the orchestrator observability database.
- `automate/instances/bootstrap/symA` contains the configuration files for symA. This is currently disabled.
- `automate/instances/bootstrap/ops-agent` contains the ops agent configuration for ingesting Symphony and HostFactory logs into Cloud Logging.

### Host Factory Wrapper

In order to test the previous deployment / boostraping, one can use the Python HostFactory API wrapper through the `outils/HFWrapper/play.ipynb` jupyter notebook.

### Observability

If one properly configured the orchestrator bigquery tables and ingestors, one can use the `outils/BQExplorer` to explore available ingested data. 











