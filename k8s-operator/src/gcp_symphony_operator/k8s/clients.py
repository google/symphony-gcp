"""
Kubernetes client manager for isolating API client instances per handler.
"""

import asyncio
import concurrent.futures
import contextlib
from typing import Optional

import kubernetes.client as k8s_client
import kubernetes.config as k8s_config
from gcp_symphony_operator.config import Config, get_config_sync

_executor = concurrent.futures.ThreadPoolExecutor()


class KubernetesClientManager:
    """
    Manages Kubernetes API clients for a specific handler or operation.
    Each handler should create its own instance of this class.
    """

    def __init__(self, config: Optional[Config] = None):
        """Initialize a new client manager."""
        self.config = config if config else get_config_sync()
        self._api_client = None
        self._config_loaded = False

    def _ensure_config_loaded(self) -> None:
        """Ensure Kubernetes configuration is loaded."""
        if not self._config_loaded:
            try:
                k8s_config.load_incluster_config()
            except k8s_config.config_exception.ConfigException:
                k8s_config.load_kube_config(config_file=self.config.kubeconfig_path)
            self._config_loaded = True

    async def _run_in_thread(self, func, *args, **kwargs):
        """Run a function in a thread to avoid blocking the event loop."""
        loop = asyncio.get_running_loop()

        # Create a wrapper function that will receive the kwargs
        # This allows us to pass the function without args to run_in_executor
        # and still use the args and kwargs when calling it.
        def wrapper():
            return func(*args, **kwargs)

        # Pass just the wrapper with no args to run_in_executor
        return await loop.run_in_executor(_executor, wrapper)

    @contextlib.asynccontextmanager
    async def get_api_client(self):
        """Get a Kubernetes API client."""
        self._ensure_config_loaded()
        with k8s_client.ApiClient() as api_client:
            yield api_client

    @contextlib.asynccontextmanager
    async def get_core_v1_api(self):
        """Get a Core V1 API client."""
        await self._run_in_thread(self._ensure_config_loaded)
        api_client = k8s_client.ApiClient()
        core_v1 = k8s_client.CoreV1Api(api_client)
        try:
            yield core_v1
        finally:
            api_client.close()

    @contextlib.asynccontextmanager
    async def get_apps_v1_api(self):
        """Get an Apps V1 API client."""
        await self._run_in_thread(self._ensure_config_loaded)
        api_client = k8s_client.ApiClient()
        apps_v1 = k8s_client.AppsV1Api(api_client)
        try:
            yield apps_v1
        finally:
            api_client.close()

    @contextlib.asynccontextmanager
    async def get_rbac_v1_api(self):
        """Get an RBAC V1 API client."""
        await self._run_in_thread(self._ensure_config_loaded)
        api_client = k8s_client.ApiClient()
        rbac_v1 = k8s_client.RbacAuthorizationV1Api(api_client)
        try:
            yield rbac_v1
        finally:
            api_client.close()

    @contextlib.asynccontextmanager
    async def get_custom_objects_api(self):
        """Get a Custom Objects API client."""
        await self._run_in_thread(self._ensure_config_loaded)
        api_client = k8s_client.ApiClient()
        custom_obj = k8s_client.CustomObjectsApi(api_client)
        try:
            yield custom_obj
        finally:
            api_client.close()

    @contextlib.asynccontextmanager
    async def get_api_ext_v1_api(self):
        """Get an API Extensions V1 API client."""
        await self._run_in_thread(self._ensure_config_loaded)
        api_client = k8s_client.ApiClient()
        ext_v1 = k8s_client.ApiextensionsV1Api(api_client)
        try:
            yield ext_v1
        finally:
            api_client.close()
