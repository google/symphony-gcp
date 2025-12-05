# GCP Symphony Operator Environment Variables Documentation

This document outlines all user-adjustable environment variables for the GCP Symphony Operator. All environment variables use the prefix `GCP_HF_` by default, but this can be changed using the `ENV_VAR_PREFIX` environment variable. *Note: these variables are for the operator only. Environment variables for the hf-gke cli (google-symphony-hf python package) are maintained in that [README](../../hf-provider/README.md) file)

## General Configuration

| Environment Variable | Default Value | Description |
|---------------------|---------------|-------------|
| `ENV_VAR_PREFIX` | `GCP_HF_` | Prefix for all environment variables used by the operator. Changing this will change all other environment variables to need to be prefixed with the new value. i.e., if setting this to `MY_PREFIX_`, then the `GCP_HF_DEFAULT_NAMESPACES` would need to be `MY_PREFIX_DEFAULT_NAMESPACES` within the environment. This can allow for multiple environment setups on the same cluster ***(not tested)***. |
| `GCP_HF_DEFAULT_NAMESPACES` | `['gcp-symphony']` | Default namespaces for the operator to watch.  Can be a comma-separated list. The first namespace in the list will be where the operator runs all of its processes. As of the current release, only one namespace is supported. |
| `GCP_HF_KUBECONFIG_PATH` | `/app/.kube/config` | Path to the kubeconfig file. This only needs to be set if running the operator from the command line and not within a cluster. |

## Operator Configuration / Tuning

| Environment Variable | Default Value | Description |
|---------------------|---------------|-------------|
| `GCP_HF_OPERATOR_NAME` | `gcp-symphony-operator` | Name of the operator. |
| `GCP_HF_OPERATOR_IMAGE_TAG` | `latest` | Image tag for the operator. If changed from the default, be sure to change the tag value on the operator container image in your registry. |
| `GCP_HF_OPERATOR_MANIFEST_FILE` | `{manifest_base_path}/{operator_name}.yaml.j2` | INTERNAL - Path to the operator manifest file |
| `GCP_HF_CRD_UPDATE_RETRY_COUNT` | `3` | Number of retries for CRD updates or any other Kubernetes API retry |
| `GCP_HF_CRD_UPDATE_RETRY_INTERVAL` | `0.5` | Interval between CRD update or any other Kubernetes API retries (seconds) |
| `GCP_HF_CRD_UPDATE_BATCH_SIZE` | `50` | Batch size for CRD updates. Controls the maximum number of status update events are pulled from the internal status update event queue to be sorted and deduplicated. The system pull as many events as are available up to this number. If the status update event queue goes to zero during a collection step, the status update worker will process the events that are available. |
| `GCP_HF_CRD_COMPLETED_CHECK_INTERVAL` | `30` | Interval for checking completed CRD status (minutes) |
| `GCP_HF_CRD_COMPLETED_RETAIN_TIME` | `1440` | Time to retain completed custom resources before deletion (minutes). This applies to GCPSymphonyResources in WaitingCleanup phase and MachineReturnRequests in Complete phase. 1440 minutes is equal to 24 hours. |
| `GCP_HF_CRD_DELETED_PODS_MAXIMUM` | `0` | Maximum number of deleted pods to track (0 for unlimited)  ***Not implemented*** |

## Logging Configuration

| Environment Variable | Default Value | Description |
|---------------------|---------------|-------------|
| `GCP_HF_LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `GCP_HF_LOG_FORMAT` | `%(asctime)s - %(name)s - %(levelname)s - %(message)s` | Format for log messages |
| `GCP_HF_LOG_FORMATTER` | `structured` | Log formatter type (structured, simple). Structured setting will write the log events in a JSON structure that is more easily consumable by cloud providers. The simple option is good for development environments where JSON-formatted logging can be cumbersome. |
| `GCP_HF_KUBERNETES_CLIENT_LOG_LEVEL` | Same as `LOG_LEVEL` | INTERNAL - Log level for Kubernetes client |
| `GCP_HF_KOPF_LOG_LEVEL` | Same as `LOG_LEVEL` | Log level for Kopf operator framework. Setting this value will override the value retrieved from the GCP_HF_LOG_LEVEL. This is useful so DEBUG can be enabled on the operator, but limit the amount of logging from the kopf framework. |

## Kubernetes Configuration

| Environment Variable | Default Value | Description |
|---------------------|---------------|-------------|
| `GCP_HF_KUBERNETES_RBAC_CHECK` | `False` | Whether to check RBAC permissions on operator startup. |
| `GCP_HF_KUBERNETES_CLIENT_TIMEOUT_ENABLE` | `False` | Whether to enable Kubernetes client timeout |
| `GCP_HF_KUBERNETES_CLIENT_TIMEOUT` | `10` | Timeout for Kubernetes client operations (seconds) |
| `GCP_HF_ENABLE_GKE_PREEMPTION_HANDLING` | `True` | Whether to enable the preemption handler to monitor for preemption of VMs. |
| `GCP_HF_GKE_PREEMPT_LABELS` | `{"cloud.google.com/gke-spot": "true", "cloud.google.com/gke-provisioning": "spot"}` | A dictionary listing the node labels that indicate a VM is preemptable by the Google Compute Engine. Used when _ENABLE_GKE_PREEMPTION_HANDLING is set to True |
| `GCP_HF_GKE_NODE_TAINTS_LIST` | `{"DeletionCandidateOfClusterAutoscaler", "node.cloudprovider.kubernetes.io/shutdown", "node.kubernetes.io/unschedulable"}` | A set of strings listing the possible TAINTS that GKE will apply to a node that is being preempted by Google Compute Engine. Used when _ENABLE_GKE_PREEMPTION_HANDLING is True. |

## Kopf Framework Configuration

| Environment Variable | Default Value | Description |
|---------------------|---------------|-------------|
| `GCP_HF_KOPF_SERVER_TIMEOUT` | `300` | Server timeout for Kopf operator framework (seconds) |
| `GCP_HF_KOPF_MAX_WORKERS` | `20` | Maximum number of workers for Kopf operator framework |
| `GCP_HF_KOPF_POSTING_ENABLED` | `False` | Enables/Disables the posting of Kopf operator framework events to the custom resource's Events list. Be careful when setting this as it can lead to CRD bloat in the Kubernetes etcd database. |


## INTERNAL Customizations
The following environment variables, RBAC and CRDs, are utilized internally and for the creation of the manifest files used to deploy the operator requirements into the cluster. Be sure these are in place prior to generating the manifests with the 'export-manifests' switch. (See *TBD*) It is recommended that these environment variables are left to their default values.  

## RBAC Configuration

| Environment Variable | Default Value | Description |
|---------------------|---------------|-------------|
| `GCP_HF_SERVICE_ACCOUNT_NAME` | `{operator_name}-sa` | Name of the service account |
| `GCP_HF_CLUSTER_ROLE_NAME` | `{operator_name}-cluster-role` | Name of the cluster role |
| `GCP_HF_CLUSTER_ROLE_BINDING_NAME` | `{operator_name}-cluster-role-binding` | Name of the cluster role binding |
| `GCP_HF_NAMESPACE_ROLE_NAME` | `{operator_name}-role` | Name of the namespace role |
| `GCP_HF_NAMESPACE_ROLE_BINDING_NAME` | `{operator_name}-role-binding` | Name of the namespace role binding |


## Custom Resource Definition (CRD) Configuration
The following represent values that can be updated to the user's preference. Changing these values is strictly cosmetic.

| Environment Variable | Default Value | Description |
|---------------------|---------------|-------------|
| `GCP_HF_CRD_KIND` | `GCPSymphonyResource` | Kind of the CRD |
| `GCP_HF_CRD_SHORT_NAME` | `gcpsr` | Short name of the CRD |
| `GCP_HF_CRD_GROUP` | `accenture.com` | API group of the CRD |
| `GCP_HF_CRD_SINGULAR` | `gcp-symphony-resource` | Singular name of the CRD |
| `GCP_HF_CRD_API_VERSION` | `v1` | API version of the CRD |
| `GCP_HF_CRD_FINALIZER` | `symphony-operator/finalizer` | Finalizer for the CRD |
| `GCP_HF_CRD_RETURN_REQUEST_SINGULAR` | `machine-return-request` | Singular name for MachineReturnRequest CRD |
| `GCP_HF_CRD_RETURN_REQUEST_KIND` | `MachineReturnRequest` | Kind name for MachineReturnRequest CRD |
| `GCP_HF_CRD_RETURN_REQUEST_SHORT_NAME` | `rrm` | Short name for MachineReturnRequest CRD. `mmr` is also a valid short name that is hard-coded in the manifest. |

## Manifest file generation
The following variables control from where the operator will load manifest templates used for the export-manifest command. These are not used during the operator runtime on the Kubernetes cluster.

| Environment Variable | Default Value | Description |
|---------------------|---------------|-------------|
| `GCP_HF_DEFAULT_CONTAINER_IMAGE` | `nginx:latest` | Default container image (fallback for testing). This is used for the export-manifest option only. This is the value that will be put into the base manifest provided to deploy the operator into the Kubernetes cluster. |
| `GCP_HF_MANIFEST_BASE_PATH` | `manifests` | Base path for manifest template files |
| `GCP_HF_CRD_MANIFEST_PATH` | `{manifest_base_path}/crd` | Path to CRD manifest template |
| `GCP_HF_CRD_MANIFEST_FILE` | `gcp-symphony-crd.yaml.j2` | Manifest file template for GCPSymphonyResource CRD |
| `GCP_HF_CRD_RETURN_REQUEST_MANIFEST_FILE` | `return-request-crd.yaml.j2` | Manifest file template for MachineReturnRequest CRD |
| `GCP_HF_RBAC_PATH` | `{base_manifest_path}/rbac` | Path to RBAC manifest templates |
| `GCP_HF_SERVICE_ACCOUNT_FILE` | `operator-sa.yaml.j2` | Service account manifest file template |
| `GCP_HF_RBAC_ROLE_FILE` | `operator-role.yaml.j2` | RBAC role manifest file template |
| `GCP_HF_RBAC_CLUSTER_ROLE_FILE` | `operator-clusterrole.yaml.j2` | RBAC cluster role manifest file template |
| `GCP_HF_RBAC_ROLE_BINDING_FILE` | `operator-role-binding.yaml.j2` | RBAC role binding manifest file template |
| `GCP_HF_RBAC_CLUSTER_ROLE_BINDING_FILE` | `operator-clusterrole-binding.yaml.j2` | RBAC cluster role binding manifest file template |
| `GCP_HF_NAMESPACE_MANIFEST_PATH` | `{base_manifest_path}/namespace` | Path to namespace manifest templates|
| `GCP_HF_NAMESPACE_MANIFEST_FILE` | `namespace.yaml.j2` | Namespace manifest file template |


## Pod and Container Configuration

| Environment Variable | Default Value | Description |
|---------------------|---------------|-------------|
| `GCP_HF_IMAGE_PULL_POLICY` | `IfNotPresent` | Image pull policy for containers. For performance, if the container images are large, it is recommended to leave this at `IfNotPresent` so that the image needs to be pulled only once per node. If it's necessary to require the absolute latest version of the container image, set this to `Always` |
| `GCP_HF_POD_CREATE_BATCH_SIZE` | `10` | Number of pods to create before taking a breath and continuing until all requested pods have been submitted. |
| `GCP_HF_POD_GRACE_PERIOD` | `30` | The default grace period for pod termination (seconds) |
| `GCP_HF_SYSTEM_INITIATED_RETURN_MSG` | `system-initiated-return` | For the GCPSymphonyResource Status.returnedMachines[].returnRequestId. Normally the returnRequestId would be the requestId of the MachineReturnRequest custom resource created to return the machine. If a ReturnedMachine entry has this value, it indicates that the pod was deleted manually or by system-initiated events, like a spot VM preemption. |

## Scaling Configuration

| Environment Variable | Default Value | Description |
|---------------------|---------------|-------------|
| `GCP_HF_MINIMUM_MACHINE_COUNT` | `1` | Minimum number of machines |
| `GCP_HF_MAXIMUM_MACHINE_COUNT` | `1000` | Maximum number of machines (0 for no maximum) **This feature has not been implemented** |

## Request ID Configuration
The following environment variables pertain to the GCP-Symphony-Operator's internal request IDs.
These values will be visible in `kubectl get|describe gcpsr` commands, if they are present

| Environment Variable | Default Value | Description |
|---------------------|---------------|-------------|
| `GCP_HF_MIN_REQUEST_ID_LENGTH` | `8` | INTERNAL - Minimum length for request IDs |
| `GCP_HF_REQUEST_ID_INTERNAL_PREFIX` | `int-` | Prefix for GCPSymphonyResource requests that were submitted without a supplied request ID, such that the hf-gke cli provides. |
| `GCP_HF_PREEMPTED_MACHINE_REQUEST_ID_PREFIX` | `prmt-` | Prefix for MachineReturnRequest ids representing when the Kubernetes cluster system has preempted a cluster node. |

## Health Check Configuration
The operator has a health check server to provide a readiness probe for the pod in which the container is running.

| Environment Variable | Default Value | Description |
|---------------------|---------------|-------------|
| `GCP_HF_HEALTH_CHECK_ENABLED` | `True` | Whether to enable health check server |
| `GCP_HF_HEALTH_CHECK_PORT` | `8080` | Port for health check server |
| `GCP_HF_HEALTH_CHECK_PATH` | `/health` | Path for health check endpoint |
| `GCP_HF_READINESS_CHECK_PATH` | `/ready` | Path for readiness check endpoint |


## Usage Notes

1.  All environment variables use the prefix defined by `ENV_VAR_PREFIX` (default: `GCP_HF_`).
2.  Boolean values can be set using 'true', '1', or 'yes' (case-insensitive) for true, and any other value for false.
3.  Numeric values are converted to integers or floats as appropriate. If placing them in a deployment manifest, they should be surrounded by quotes.
4.  Path values can be relative or absolute.
5.  For `DEFAULT_NAMESPACES`, you can provide a comma-separated list of namespaces. The first namespace in the list will be where the operator runs all of its processes. At this time, however, multiple namespace operation is not implemented.

## Example Usage

```bash
# Change the log level to DEBUG
export GCP_HF_LOG_LEVEL=DEBUG

# Set a custom kubeconfig path
export GCP_HF_KUBECONFIG=/path/to/kubeconfig

# Enable RBAC checks
export GCP_HF_KUBERNETES_RBAC_CHECK=true

# Set minimum and maximum machine counts
export GCP_HF_MINIMUM_MACHINE_COUNT=2
export GCP_HF_MAXIMUM_MACHINE_COUNT=50
```


[Back to HOME](../README.md)
