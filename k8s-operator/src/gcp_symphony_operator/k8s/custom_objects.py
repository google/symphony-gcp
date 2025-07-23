"""
This module provides functions for calling Kubernetes API to update
custom resources with retry logic. It uses the Kubernetes AsyncIO client
to perform operations on custom objects and their statuses.
"""

from functools import lru_cache
from typing import Any, Dict

from gcp_symphony_operator.config import Config, get_config_sync
from gcp_symphony_operator.k8s.clients import KubernetesClientManager
from gcp_symphony_operator.profiling import log_execution_time_with_lazy_logger
from gcp_symphony_operator.utils import retry_with_lazy_config


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
async def call_patch_namespaced_custom_object(
    namespace: str,
    name: str,
    plural: str = _get_config().crd_plural,
    patch_body: Dict[str, Any] | None = None,
) -> None:
    """Update resource metadata with retry logic."""
    k8s_client = KubernetesClientManager(_get_config())
    async with k8s_client.get_custom_objects_api() as custom_obj:
        await k8s_client._run_in_thread(
            custom_obj.patch_namespaced_custom_object,
            group=_get_config().crd_group,
            version=_get_config().crd_api_version,
            namespace=namespace,
            plural=plural,
            name=name,
            body=patch_body,
            _request_timeout=_get_config().kubernetes_client_timeout,
            # _content_type="application/merge-patch+json",
        )


@log_execution_time_with_lazy_logger(lambda: _get_config().logger)
@retry_with_lazy_config(_get_config)
async def call_patch_namespaced_custom_object_status(
    namespace: str,
    name: str,
    plural: str = _get_config().crd_plural,
    patch_body: Dict[str, Any] | None = None,
) -> None:
    """Update resource status with retry logic."""
    k8s_client = KubernetesClientManager(_get_config())
    async with k8s_client.get_custom_objects_api() as custom_obj:
        await k8s_client._run_in_thread(
            custom_obj.patch_namespaced_custom_object_status,
            group=_get_config().crd_group,
            version=_get_config().crd_api_version,
            namespace=namespace,
            plural=plural,
            name=name,
            body=patch_body,
            _request_timeout=_get_config().kubernetes_client_timeout,
        )


@log_execution_time_with_lazy_logger(lambda: _get_config().logger)
@retry_with_lazy_config(_get_config)
async def call_get_custom_object(
    name: str, namespace: str, plural: str = _get_config().crd_plural
):
    k8s_client = KubernetesClientManager(_get_config())
    async with k8s_client.get_custom_objects_api() as custom_obj:
        return await k8s_client._run_in_thread(
            custom_obj.get_namespaced_custom_object,
            group=_get_config().crd_group,
            version=_get_config().crd_api_version,
            namespace=namespace,
            plural=plural,
            name=name,
            _request_timeout=_get_config().kubernetes_client_timeout,
        )  # type: ignore


@log_execution_time_with_lazy_logger(lambda: _get_config().logger)
@retry_with_lazy_config(_get_config)
async def call_list_namespaced_custom_object(
    namespace: str = _get_config().default_namespaces[0],
    plural: str = _get_config().crd_plural,
    label_selector: str | None = None,
):
    """List namespaced custom objects with retry logic."""
    k8s_client = KubernetesClientManager(_get_config())
    async with k8s_client.get_custom_objects_api() as custom_obj:
        return await k8s_client._run_in_thread(
            custom_obj.list_namespaced_custom_object,
            group=_get_config().crd_group,
            version=_get_config().crd_api_version,
            plural=plural,
            namespace=namespace,
            label_selector=label_selector,
        )


@log_execution_time_with_lazy_logger(lambda: _get_config().logger)
@retry_with_lazy_config(_get_config)
async def call_delete_namespaced_custom_object(
    name: str | None = None,
    namespace: str = _get_config().default_namespaces[0],
    plural: str = _get_config().crd_plural,
):
    """Delete a namespaced custom object with retry logic."""
    k8s_client = KubernetesClientManager(_get_config())
    async with k8s_client.get_custom_objects_api() as custom_obj:
        await k8s_client._run_in_thread(
            custom_obj.delete_namespaced_custom_object,
            group=_get_config().crd_group,
            version=_get_config().crd_api_version,
            name=name,
            namespace=namespace,
            plural=plural,
        )


@log_execution_time_with_lazy_logger(lambda: _get_config().logger)
@retry_with_lazy_config(_get_config)
async def call_create_namespaced_custom_object(
    body: Dict[str, Any],
    plural: str,
    namespace: str = _get_config().default_namespaces[0],
):
    k8s_client = KubernetesClientManager(_get_config())
    async with k8s_client.get_custom_objects_api() as custom_obj:
        return await k8s_client._run_in_thread(
            custom_obj.create_namespaced_custom_object,
            group=_get_config().crd_group,
            version=_get_config().crd_api_version,
            namespace=namespace,
            plural=plural,
            body=body,
        )
