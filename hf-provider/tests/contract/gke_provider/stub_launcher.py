import datetime
import json
import os
import warnings
from pathlib import Path
from typing import Any, Optional

# kubernetes and gke_provider are imported inside functions. main() must call
# bootstrap_logging() before any third-party import.

CLUSTER_STATE_PATH_ENV = "CONTRACT_CLUSTER_STATE_PATH"


def _matches_labels(labels: dict[str, str], label_selector: Optional[str]) -> bool:
    """Check labels against a selector of comma-separated key=value terms."""
    if not label_selector:
        return True
    for term in label_selector.split(","):
        key, _, value = term.partition("=")
        if labels.get(key) != value:
            return False
    return True


class _StubCustomObjectsApi:
    """A CustomObjectsApi that reads custom resources from the cluster state file."""

    def __init__(self, state: dict[str, Any]) -> None:
        self._state = state

    def _objects(self, plural: str, namespace: Optional[str]) -> list[dict[str, Any]]:
        objects = self._state["custom_objects"].get(plural, [])
        if namespace is None:
            return objects
        return [obj for obj in objects if obj["metadata"].get("namespace") == namespace]

    def create_namespaced_custom_object(
        self,
        group: str,
        version: str,
        namespace: str,
        plural: str,
        body: dict[str, Any],
        **_kwargs: object,
    ) -> dict[str, Any]:
        # Used by the #86 warning test.
        warnings.warn("contract-canary: warning raised inside the provider")

        metadata = dict(body.get("metadata", {}))
        metadata["name"] = metadata.get("generateName", "") + "contract"
        metadata["namespace"] = namespace
        metadata["resourceVersion"] = "1"
        metadata["uid"] = "contract-uid"

        created = dict(body)
        created["metadata"] = metadata
        return created

    def list_namespaced_custom_object(
        self,
        group: str,
        version: str,
        namespace: str,
        plural: str,
        label_selector: Optional[str] = None,
        **_kwargs: object,
    ) -> dict[str, Any]:
        items = [
            obj
            for obj in self._objects(plural, namespace)
            if _matches_labels(obj["metadata"].get("labels", {}), label_selector)
        ]
        return {"apiVersion": f"{group}/{version}", "kind": "List", "items": items}

    def list_cluster_custom_object(
        self, group: str, version: str, plural: str, **_kwargs: object
    ) -> dict[str, Any]:
        items = self._objects(plural, None)
        return {"apiVersion": f"{group}/{version}", "kind": "List", "items": items}

    def get_namespaced_custom_object(
        self, group: str, version: str, namespace: str, plural: str, name: str, **_kwargs: object
    ) -> dict[str, Any]:
        from kubernetes.client.rest import ApiException

        for obj in self._objects(plural, namespace):
            if obj["metadata"].get("name") == name:
                return obj
        raise ApiException(status=404, reason="Not Found")


class _StubCoreV1Api:
    """A CoreV1Api that lists pods from the cluster state file."""

    def __init__(self, state: dict[str, Any]) -> None:
        self._state = state

    def list_namespaced_pod(
        self, namespace: str, label_selector: Optional[str] = None, **_kwargs: object
    ) -> Any:
        from kubernetes import client

        items = []
        for pod in self._state["pods"]:
            if pod["namespace"] != namespace:
                continue
            if not _matches_labels(pod["labels"], label_selector):
                continue
            start_time = None
            if pod["start_time"] is not None:
                start_time = datetime.datetime.fromisoformat(pod["start_time"])
            items.append(
                client.V1Pod(
                    metadata=client.V1ObjectMeta(
                        name=pod["name"],
                        uid=pod["uid"],
                        namespace=pod["namespace"],
                        labels=pod["labels"],
                    ),
                    status=client.V1PodStatus(
                        phase=pod["phase"],
                        pod_ip=pod["pod_ip"],
                        start_time=start_time,
                    ),
                )
            )
        return client.V1PodList(items=items)


def _install_stub() -> None:
    """Replace the Kubernetes API factories with stub clients that read the cluster state file."""
    from gke_provider.k8s import resources

    state = json.loads(Path(os.environ[CLUSTER_STATE_PATH_ENV]).read_text())

    custom_objects = _StubCustomObjectsApi(state)
    core = _StubCoreV1Api(state)
    resources.custom_obj_api = lambda: custom_objects
    resources.core_client = lambda: core


def main() -> None:
    """Run the real CLI with the stub clients installed."""
    from common.log_bootstrap import bootstrap_logging

    bootstrap_logging()

    _install_stub()

    from gke_provider.__main__ import main as cli_main

    cli_main()


if __name__ == "__main__":
    main()
