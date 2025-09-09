null = None

class AdvancedDotDict(dict):
    """Dictionary with dot notation and nested dictionary conversion"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Convert nested dictionaries
        for key, value in self.items():
            if isinstance(value, dict) and not isinstance(value, AdvancedDotDict):
                self[key] = AdvancedDotDict(value)
    
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{key}'")
    
    def __setattr__(self, key, value):
        if isinstance(value, dict) and not isinstance(value, AdvancedDotDict):
            value = AdvancedDotDict(value)
        self[key] = value
    
    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{key}'")

def create_pods(log: dict):
    log = AdvancedDotDict(log)
    return {
        "time": log.protoPayload.response.metadata.creationTimestamp,
        "cluster": log.resource.labels.cluster_name,
        "namespace": log.protoPayload.request.metadata.namespace,
        "source": "audit",
        "run": "${run_id}",
        "event": "pod:create",
        "sym_request": log.protoPayload.request.metadata.labels["symphony.requestId"],
        "container_name": log.protoPayload.request.spec.containers[0]["name"],
        "pod": log.protoPayload.request.metadata.name,
        "node": None,
        "acn": log.protoPayload.request.metadata.labels.app,
        "detail": None
    }

def container_started(log: dict):
    log = AdvancedDotDict(log)
    return {
        "time": log.timestamp,
        "cluster": log.resource.labels.cluster_name,
        "namespace": log.resource.labels.namespace_name,
        "source": "k8s-api-log",
        "run": "${run_id}",
        "event": "pod:ready",
        "sym_request": None,
        "container_name": None,
        "pod": log.resource.labels.pod_name,
        "node": log.jsonPayload.source.host,
        "acn": None,
        "detail": None,
    }

def pod_scheduled(log: dict):
    log = AdvancedDotDict(log)
    return {
        "time": log.timestamp,
        "cluster": log.resource.labels.cluster_name,
        "namespace": log.protoPayload.request.metadata.namespace,
        "source": "audit",
        "run": "${run_id}",
        "event": "pod:scheduled",
        "sym_request": None,
        "container_name": None,
        "pod": log.protoPayload.request.metadata.name,
        "node": log.protoPayload.request.target.name,
        "acn": None,
        "detail": None,
    }

def nodes_delete(log: dict):
    log = AdvancedDotDict(log)
    return {
        "time": log.timestamp,
        "cluster": log.resource.labels.cluster_name,
        "namespace": None,
        "source": "audit",
        "run": "${run_id}",
        "event": "node:delete",
        "sym_request": None,
        "container_name": None,
        "pod": None,
        "node": log.protoPayload.response.details.name,
        "acn": None,
        "detail": None,
    }

def nodes_create(log: dict):
    log = AdvancedDotDict(log)
    return {
        "time":  log.protoPayload.response.metadata.creationTimestamp,
        "cluster":  log.resource.labels.cluster_name,
        "namespace": None,
        "source": "audit",
        "run":  "${run_id}",
        "event": "node:create",
        "sym_request": None,
        "container_name": null,
        "pod": null,
        "node": log.protoPayload.response.metadata.name,
        "acn": null,
        "detail": null,
    }

def node_ready_patch(log: dict):
    log = AdvancedDotDict(log)
    res = log.protoPayload.response
    conditions = res.status.conditions
    time = [condition for condition in conditions if condition["type"] == "Ready" and condition["status"] == "True"][0]["lastTransitionTime"]
    return {
        "time": time,
        "cluster": log.resource.labels.cluster_name,
        "namespace": null,
        "source": "audit",
        "run": "${run_id}",
        "event": "node:ready_patch",
        "sym_request": null,
        "container_name": null,
        "pod": null,
        "node": res.metadata.name,
        "acn": null,
        "detail": conditions
    }