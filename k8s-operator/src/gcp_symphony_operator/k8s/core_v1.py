"""
This module provides functions for calling Kubernetes API to update
core resources with retry logic. It uses the Kubernetes AsyncIO client
to perform operations on core objects and their statuses.
"""

from functools import lru_cache

from gcp_symphony_operator.config import Config, get_config_sync
from gcp_symphony_operator.k8s.clients import KubernetesClientManager
from gcp_symphony_operator.profiling import log_execution_time_with_lazy_logger
from gcp_symphony_operator.utils import retry_with_lazy_config
from kubernetes.client import V1Pod, V1PodList


@lru_cache(maxsize=1)
def _get_config() -> Config:
    """Get the configuration object."""
    try:
        config = get_config_sync()
        return config
    except Exception as e:
        raise RuntimeError(
            f"Failed to get configuration. Ensure Config is initialized properly.\n{e}"
        )


@log_execution_time_with_lazy_logger(lambda: _get_config().logger)
@retry_with_lazy_config(_get_config)
async def call_create_pod(pod_body: dict, namespace: str) -> V1Pod:
    k8s_client = KubernetesClientManager(_get_config())
    async with k8s_client.get_core_v1_api() as core_v1:
        try:
            return await k8s_client._run_in_thread(
                core_v1.create_namespaced_pod,
                namespace=namespace,
                body=pod_body,
                _request_timeout=_get_config().kubernetes_client_timeout,
            )
        except Exception as e:
            _get_config().logger.exception(f"Failed to create pod: {e}")
            raise


@log_execution_time_with_lazy_logger(lambda: _get_config().logger)
@retry_with_lazy_config(_get_config)
async def call_list_namespaced_pod(namespace: str, label_selector: str) -> V1PodList:
    """Retryable function to get the list of pods in a namespace."""
    k8s_client = KubernetesClientManager(_get_config())
    async with k8s_client.get_core_v1_api() as core_v1:
        return await k8s_client._run_in_thread(
            core_v1.list_namespaced_pod,
            namespace=namespace,
            label_selector=label_selector,
            _request_timeout=_get_config().kubernetes_client_timeout,
        )


@log_execution_time_with_lazy_logger(lambda: _get_config().logger)
@retry_with_lazy_config(_get_config)
async def call_patch_namespaced_pod(name: str, namespace: str, body: dict):
    k8s_client = KubernetesClientManager(_get_config())
    async with k8s_client.get_core_v1_api() as core_v1:
        return await k8s_client._run_in_thread(
            core_v1.patch_namespaced_pod,
            name=name,
            namespace=namespace,
            body=body,
            _request_timeout=_get_config().kubernetes_client_timeout,
            # _content_type="application/merge-patch+json",
        )  # type: ignore


@log_execution_time_with_lazy_logger(lambda: _get_config().logger)
async def call_delete_namespaced_pod(name: str, namespace: str):
    """Delete a pod in a specific namespace."""
    k8s_client = KubernetesClientManager(_get_config())
    async with k8s_client.get_core_v1_api() as core_v1:
        return await k8s_client._run_in_thread(
            core_v1.delete_namespaced_pod,
            name=name,
            namespace=namespace,
            _request_timeout=_get_config().kubernetes_client_timeout,
        )  # type: ignore


@log_execution_time_with_lazy_logger(lambda: _get_config().logger)
async def call_list_pod_for_namespace_on_node(
    field_selector: str,
    label_selector: str,
    namespace: str = _get_config().default_namespaces[0],
):
    """
    List all pods a namespace for a specific  node.
    It's possible a node can have pods from multiple namespaces,
    but we're only interested in one namespace.
    """
    k8s_client = KubernetesClientManager(_get_config())
    async with k8s_client.get_core_v1_api() as core_v1:
        return await k8s_client._run_in_thread(
            core_v1.list_namespaced_pod,
            namespace=namespace,
            label_selector=label_selector,
            field_selector=field_selector,
        )


@log_execution_time_with_lazy_logger(lambda: _get_config().logger)
async def call_read_namespaced_pod(
    name: str, namespace: str = _get_config().default_namespaces[0]
):
    """
    Get a specific pod by name in a namespace.
    """
    k8s_client = KubernetesClientManager(_get_config())
    async with k8s_client.get_core_v1_api() as core_v1:
        return await k8s_client._run_in_thread(
            core_v1.read_namespaced_pod,
            name=name,
            namespace=namespace,
        )
