"""
Pytest configuration file with fixtures for testing the k8s-operator.
"""

import os
import sys
import threading
from typing import Any, Dict, Generator, List, Literal, Union
from unittest.mock import AsyncMock, MagicMock, patch

import pytest  # noqa

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)
from gcp_symphony_operator.config import Config  # noqa

pytest_plugins = ["pytest_asyncio"]  # noqa: E402


@pytest.fixture
async def mock_config() -> Config:
    """Fixture to provide a mock Config instance."""
    config = await Config.create(thin=True)
    config.default_namespaces = ["test-namespace"]
    config.service_account_name = "test-sa"
    config.cluster_role_name = "test-cluster-role"
    config.cluster_role_binding_name = "test-cluster-role-binding"
    config.namespace_role_name = "test-role"
    config.namespace_role_binding_name = "test-role-binding"
    config.operator_name = "test-operator"
    config.crd_group = "test-group"
    config.crd_api_version = "test-version"
    config.crd_plural = "test-plural"
    config.crd_kind = "TestKind"
    config.crd_return_request_kind = "TestReturnRequestKind"
    config.crd_return_request_plural = "test-return-requests"
    config.kubernetes_client_timeout = 10
    config.default_minimum_machine_count = 1
    config.pod_create_batch_size = 1
    config.default_pod_grace_period = 30
    config.crd_completed_check_interval = 20
    config.crd_completed_retain_time = 30
    config.crd_update_retry_count = 3
    config.request_id_internal_prefix = "int-"
    config.preempted_machine_request_id_prefix = "prmt-"
    config.logger = MagicMock()
    return config


class MockLogger:
    """A mock logger class that mimics the standard logger interface."""

    def __init__(self) -> None:
        self.debug = MagicMock()
        self.info = MagicMock()
        self.warning = MagicMock()
        self.error = MagicMock()
        self.exception = MagicMock()


@pytest.fixture
def mock_logger() -> MockLogger:
    """Fixture to provide a mock logger."""
    return MockLogger()


@pytest.fixture
def mock_queue() -> MagicMock:
    """Fixture to provide a mock queue object."""
    return MagicMock()


@pytest.fixture
def mock_k8s_api() -> Generator[Dict[str, MagicMock], Any, None]:
    """Fixture to provide mock Kubernetes API clients."""
    with patch("kubernetes.client.CoreV1Api") as mock_core_api, patch(
        "kubernetes.client.RbacAuthorizationV1Api"
    ) as mock_rbac_api, patch(
        "kubernetes.client.ApiextensionsV1Api"
    ) as mock_apiext_api, patch(
        "kubernetes.client.CustomObjectsApi"
    ) as mock_custom_api:

        # Configure the mock returns
        mock_core_api_instance = MagicMock()
        mock_rbac_api_instance = MagicMock()
        mock_apiext_api_instance = MagicMock()
        mock_custom_api_instance = MagicMock()

        mock_core_api.return_value = mock_core_api_instance
        mock_rbac_api.return_value = mock_rbac_api_instance
        mock_apiext_api.return_value = mock_apiext_api_instance
        mock_custom_api.return_value = mock_custom_api_instance

        yield {
            "core": mock_core_api_instance,
            "rbac": mock_rbac_api_instance,
            "apiext": mock_apiext_api_instance,
            "custom": mock_custom_api_instance,
        }


@pytest.fixture
def mock_kopf() -> Generator[Union[MagicMock, AsyncMock], Any, None]:
    """Fixture to provide mock kopf module."""
    with patch("kopf") as mock_kopf_module:
        yield mock_kopf_module


@pytest.fixture
def mock_pod() -> MagicMock:
    """Fixture to provide a mock pod object."""
    pod = MagicMock()

    # pod.metadata = MagicMock()
    def metadata_get_side_effect(
        key: str, default: Union[str, None] = None
    ) -> Union[str, Dict[str, Any], List[Dict[str, Any]], None]:
        if key == "name":
            return "test-pod"
        elif key == "namespace":
            return "test-namespace"
        elif key == "labels":
            return {
                "managed-by": "test-operator",
                "app": "test-owner",
                "symphony.requestId": "test-request-id",
                "symphony.deleteRequestId": "test-delete-request-id",
            }
        elif key == "ownerReferences":
            return [
                {
                    "apiVersion": "test-group/test-version",
                    "kind": "TestKind",
                    "name": "test-owner",
                    "uid": "test-uid",
                }
            ]
        else:  # pragma: no cover
            return default

    pod.spec = MagicMock()
    pod.status = MagicMock()
    pod.metadata.get = metadata_get_side_effect
    # name = "test-pod"
    # pod.metadata.namespace = "test-namespace"
    # pod.metadata.labels = {
    #     "managed-by": "test-operator",
    #     "app": "test-owner",
    #     "symphony.requestId": "test-request-id",
    #     "symphony.deleteRequestId": "test-delete-request-id",
    # }
    # pod.metadata.ownerReferences = [
    #     {
    #         "apiVersion": "test-group/test-version",
    #         "kind": "TestKind",
    #         "name": "test-owner",
    #         "uid": "test-uid",
    #     }
    # ]

    def side_effect(key: str, default: str = "test") -> Union[str, Dict[str, Any]]:
        if key == "name":
            return str(pod.metadata.name)
        elif key == "namespace":
            return str(pod.metadata.namespace)
        elif key == "labels":
            return dict(pod.metadata.labels)
        elif key == "ownerReferences":
            return dict(pod.metadata.ownerReferences)
        else:
            return default

    pod.metadata.get.side_effect = side_effect
    return pod


@pytest.fixture
def mock_meta() -> MagicMock:
    """Fixture to provide a mock meta object."""
    meta = MagicMock()
    meta["name"] = "test-resource"
    meta["namespace"] = "test-namespace"
    meta["uid"] = "test-uid"
    meta["annotations"] = {"test-annotation": "test-value"}
    meta["labels"] = {
        "test-label": "test-value",
        "symphony.requestId": "test-request-id",
    }

    def get_side_effect(
        key: str, default: Union[str, None] = None
    ) -> dict[str, str] | None | Any | Literal["test-resource"] | ...:  # type: ignore  # noqa: E501
        if key == "name":
            return "test-resource"
        elif key == "namespace":
            return "test-namespace"
        elif key == "uid":
            return "test-uid"
        elif key == "labels":
            return {"test-label": "test-value", "symphony.requestId": "test-request-id"}
        elif key == "annotations":
            return {"test-annotation": "test-value"}
        elif key == "ownerReferences":
            return {
                "apiVersion": "test-group/test-version",
                "kind": "TestKind",
                "name": "test-owner",
                "uid": "test-uid",
            }
        else:
            return default

    meta.get.side_effect = get_side_effect
    return meta


@pytest.fixture
def mock_spec() -> MagicMock:
    """Fixture to provide a mock spec object."""
    spec = MagicMock()
    spec["image"] = "test-image"
    spec["containerPort"] = 8080
    spec["hostPort"] = 80
    spec["podSpec"] = {
        "containers": [{"name": "test-container", "image": "test-image"}]
    }

    def get_side_effect(
        key: str, default: Union[str, None] = None
    ) -> Union[str, int, Dict[str, Any], None]:
        if key == "machineCount":
            return 2  # Example value for machineCount
        elif key == "batchSize":
            return 1  # Example value for batchSize
        elif key == "podSpec":
            return dict(spec["podSpec"])
        else:
            return default

    spec.get.side_effect = get_side_effect

    return spec


@pytest.fixture
def mock_custom_obj_api() -> MagicMock:
    """Fixture to provide a mock CustomObjectsApi object."""
    return MagicMock()


@pytest.fixture
def mock_core_v1_api() -> MagicMock:
    """Fixture to provide a mock CoreV1Api object."""
    return MagicMock()


@pytest.fixture
def stop_event() -> threading.Event:
    """Fixture to provide a stop event."""
    return threading.Event()


@pytest.fixture
def mock_container_status() -> MagicMock:
    container_status = MagicMock()
    container_status.name = "test-container"
    container_status.state = {"running": {}}
    container_status.ready = True
    return container_status
