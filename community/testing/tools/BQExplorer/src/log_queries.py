

CREATE_PODS="""
resource.type="k8s_cluster" 
resource.labels.cluster_name="{CLUSTER_NAME}"
log_id("cloudaudit.googleapis.com/activity")
protoPayload.methodName="io.k8s.core.v1.pods.create" 
protoPayload.status.code=0
protoPayload.request.metadata.labels."managed-by"="gcp-symphony-operator"
(timestamp >= "{START_WINDOW}" AND timestamp <= "{STOP_WINDOW}")
"""

SCALE_UP_DECISION="""
logName="projects/{PROJECT_ID}/logs/container.googleapis.com%2Fcluster-autoscaler-visibility"
resource.labels.cluster_name="{CLUSTER_NAME}"
jsonPayload.decision.scaleUp:*
(timestamp >= "{START_WINDOW}" AND timestamp <= "{STOP_WINDOW}")
"""

NODE_READY="""
resource.type="k8s_node"
jsonPayload.message:"NodeReady"
resource.labels.cluster_name="{CLUSTER_NAME}"
(timestamp >= "{START_WINDOW}" AND timestamp <= "{STOP_WINDOW}")
"""

NODE_READY_PATCH="""
log_id("cloudaudit.googleapis.com/activity")
resource.labels.cluster_name="{CLUSTER_NAME}"
resource.type="k8s_cluster"
protoPayload.methodName="io.k8s.core.v1.nodes.patch"
protoPayload.response.status.conditions.reason="KubeletReady"
protoPayload.response.status.conditions.type="Ready"
protoPayload.authenticationInfo.principalEmail="system:serviceaccount:kube-system:node-controller"
(timestamp >= "{START_WINDOW}" AND timestamp <= "{STOP_WINDOW}")
"""

POD_SCHEDULED="""
protoPayload.methodName="io.k8s.core.v1.pods.binding.create"
protoPayload.request.metadata.namespace="gcp-symphony"
protoPayload.response.kind="Status"
protoPayload.response.status="Success"
resource.labels.cluster_name="{CLUSTER_NAME}"
(timestamp >= "{START_WINDOW}" AND timestamp <= "{STOP_WINDOW}")
"""

CONTAINER_STARTED_PATCH="""
resource.type="k8s_cluster"
log_id("cloudaudit.googleapis.com/activity")
protoPayload.methodName="io.k8s.core.v1.pods.patch"
protoPayload.response.status.containerStatuses.started="true"
protoPayload.response.status.containerStatuses.restartCount=0
protoPayload.response.metadata.labels."managed-by"="gcp-symphony-operator"
resource.labels.cluster_name="{CLUSTER_NAME}"
(timestamp >= "{START_WINDOW}" AND timestamp <= "{STOP_WINDOW}")
"""

# Equivalent for created with reason="Created"
# Equivalent for pulling with reason="Pulling"
CONTAINER_STARTED="""
resource.type="k8s_pod" AND
resource.labels.namespace_name="gcp-symphony"
jsonPayload.reason="Started"
resource.labels.cluster_name="{CLUSTER_NAME}"
(timestamp >= "{START_WINDOW}" AND timestamp <= "{STOP_WINDOW}")
"""

DELETE_PODS="""
resource.type="k8s_cluster" 
resource.labels.cluster_name="{CLUSTER_NAME}"
log_id("cloudaudit.googleapis.com/activity") 
protoPayload.methodName="io.k8s.core.v1.pods.delete" 
protoPayload.status.code=0
protoPayload.authenticationInfo.principalEmail=~"system:node:*"
-- Deletion by node and note operator modification
protoPayload.response.metadata.labels."managed-by"="gcp-symphony-operator"
(timestamp >= "{START_WINDOW}" AND timestamp <= "{STOP_WINDOW}")
"""

SCALE_DOWN_DECISION="""
logName="projects/{PROJECT_ID}/logs/container.googleapis.com%2Fcluster-autoscaler-visibility"
resource.labels.cluster_name="{CLUSTER_NAME}"
jsonPayload.decision.scaleDown:*
(timestamp >= "{START_WINDOW}" AND timestamp <= "{STOP_WINDOW}")
"""

NODE_CORDONED="""
resource.type="k8s_node"
jsonPayload.message:"toBeDeleted"
resource.labels.cluster_name="{CLUSTER_NAME}"
(timestamp >= "{START_WINDOW}" AND timestamp <= "{STOP_WINDOW}")
"""

NODE_NOT_READY="""
resource.type="k8s_node"
jsonPayload.message:"NodeNotReady"
resource.labels.cluster_name="{CLUSTER_NAME}"
(timestamp >= "{START_WINDOW}" AND timestamp <= "{STOP_WINDOW}")
"""

NODE_DELETED="""
resource.type="k8s_node"
jsonPayload.message:"Deleting node"
resource.labels.cluster_name="{CLUSTER_NAME}"
(timestamp >= "{START_WINDOW}" AND timestamp <= "{STOP_WINDOW}")
"""

NODES_CREATE="""
log_id("cloudaudit.googleapis.com/activity")
protoPayload.methodName="io.k8s.core.v1.nodes.create"
resource.type="k8s_cluster"
protoPayload.status.code=0
resource.labels.cluster_name="{CLUSTER_NAME}"
(timestamp >= "{START_WINDOW}" AND timestamp <= "{STOP_WINDOW}")
"""

NODES_DELETE="""
log_id("cloudaudit.googleapis.com/activity")
protoPayload.methodName="io.k8s.core.v1.nodes.delete"
resource.type="k8s_cluster"
protoPayload.status.code=0
protoPayload.response.status="Success"
resource.labels.cluster_name="{CLUSTER_NAME}"
(timestamp >= "{START_WINDOW}" AND timestamp <= "{STOP_WINDOW}")
"""