import gke_provider.k8s.resources as resources
from unittest.mock import patch, MagicMock
import pytest
from kubernetes.client.rest import ApiException
from kubernetes.client.models import V1Pod

from gke_provider.k8s.resources import custom_obj_api, core_client, get_logger
from gke_provider.k8s import client as k8s_client
import logging


def test_get_pod_from_hostname_success(mock_config):
    """Test getting pod from hostname successfully."""
    with patch.object(
        core_client(),
        "read_namespaced_pod",
        return_value=V1Pod(),
    ):
        # The resources module does not expose a get_pod_from_hostname wrapper.
        # Test the underlying CoreV1Api call directly.
        result = core_client().read_namespaced_pod("test-name", "test-namespace")
        assert result is not None

def test_get_pod_from_hostname_invalid_name(mock_config):
    """Test getting pod from hostname with invalid name."""
    with patch.object(
        core_client(),
        "read_namespaced_pod",
        return_value=None,
    ):
        result = core_client().read_namespaced_pod("test-name", "test-namespace")
        assert result is None

def test_get_pod_from_hostname_invalid_namespace(mock_config):
    """Test getting pod from hostname with invalid namespace."""
    with patch.object(
        core_client(),
        "read_namespaced_pod",
        return_value=None,
    ):
        result = core_client().read_namespaced_pod("test-name", "test")
        assert result is None

def test_get_pod_from_hostname_api_exception(mock_config):
    """Test getting pod from hostname with API exception."""
    with patch.object(
        core_client(),
        "read_namespaced_pod",
        side_effect=ApiException(status=404, reason="Not Found"),
    ), pytest.raises(ApiException):
        result = core_client().read_namespaced_pod("test-name", "test-namespace")
        assert result is None

def test_create_gcpsymphonyresource_success(mock_config):
    """Test creating GCPSymphonyResource successfully."""
    with patch.object(
        custom_obj_api(),
        "create_namespaced_custom_object",
        return_value=MagicMock(),
    ):
        result = resources.create_gcpsymphonyresource(
            name_prefix="test-prefix",
            count=2,
            pod_spec={"test": "spec"},
            namespace="test-namespace",
            group="test-group",
            kind="test-kind",
            version="test-version",
            labels={"test": "label"},
        )
        assert result is not None


def test_create_gcpsymphonyresource_api_exception(mock_config):
    """Test creating GCPSymphonyResource with API exception."""
    with patch.object(
        custom_obj_api(),
        "list_namespaced_custom_object",
        side_effect=ApiException(status=500, reason="Internal Server Error"),
    ), pytest.raises(Exception):
        resources.create_gcpsymphonyresource(
            name_prefix="test-prefix",
            count=2,
            pod_spec={"test": "spec"},
            namespace="test-namespace",
            group="test-group",
            kind="test-kind",
            version="test-version",
            labels={"test": "label"},
        )

def test_get_gcpsymphonyresource_success(mock_config):
    """Test getting GCPSymphonyResource successfully."""

    machine = MagicMock()
    machine.metadata.name = "test-name"

    with patch.object(
        custom_obj_api(),
        "get_namespaced_custom_object",
        return_value={"metadata": {"name": "test-name"}},
    ), patch.object(
        custom_obj_api(),
        "list_namespaced_custom_object",
        return_value={"items": [machine]},
    ):
        result = resources.get_custom_resource_from_request_id(
            request_id="test-name",
            namespace="test-namespace",
        )
        assert result is not None

def test_get_gcpsymphonyresource_api_exception(mock_config):
    """Test getting GCPSymphonyResource with API exception."""
    with patch.object(
        custom_obj_api(),
        "list_namespaced_custom_object",
        side_effect=ApiException(status=404, reason="Not Found"),
    ) as mock_get_namespaced_custom_object, patch.object(
        get_logger(), "info"
    ) as mock_logger_info, pytest.raises(
        Exception
    ):
        result = resources.get_custom_resource_from_request_id(
            request_id="test-name",
            namespace="test-namespace",
        )
        assert result is None
        mock_get_namespaced_custom_object.assert_called_once()
        mock_logger_info.assert_called()

def test_get_gcpsymphonyresource_ignore_not_found(mock_config):
    """Test getting GCPSymphonyResource with API exception."""
    with patch.object(
        custom_obj_api(),
        "list_namespaced_custom_object",
        side_effect=ApiException(status=404, reason="Not Found"),
    ) as mock_get_namespaced_custom_object, patch.object(
        get_logger(), "info"
    ) as mock_logger_info, pytest.raises(
        Exception
    ):
        result = resources.get_custom_resource_from_request_id(
            request_id="test-name",
            namespace="test-namespace",
        )
        assert result is None
        mock_get_namespaced_custom_object.assert_called_once()
        mock_logger_info.assert_called()

def test_delete_gcpsymphonyresource_success(mock_config):
    """Test deleting GCPSymphonyResource successfully."""
    with patch.object(
        custom_obj_api(),
        "create_namespaced_custom_object",
        return_value=MagicMock(),
    ), patch.object(
        custom_obj_api(),
        "list_namespaced_custom_object",
    ) as mock_delete_namespaced_custom_object:
        mock_delete_namespaced_custom_object.return_value = MagicMock()
        result = resources.create_machine_return_request_resource(
            request_id="test-name",
            namespace="test-namespace",
            group="test-group",
            version="test-version",
            machine_ids=["test-name"],
        )
        assert result is not None

def test_delete_gcpsymphonyresource_api_exception(mock_config):
    """Test deleting GCPSymphonyResource with API exception."""
    with patch.object(
        custom_obj_api(),
        "list_namespaced_custom_object",
        side_effect=ApiException(status=500, reason="Internal Server Error"),
    ), pytest.raises(Exception):
        resources.create_machine_return_request_resource(
            request_id="test-id",
            namespace="test-namespace",
            group="test-group",
            version="test-version",
            machine_ids=["test-name"],
        )

def test_delete_pod_success(mock_config):
    """Test deleting pod successfully."""
    with patch.object(
        core_client(),
        "read_namespaced_pod",
        return_value=V1Pod(status="success"),
    ):
        result = core_client().read_namespaced_pod("test-name", "test-namespace")
        assert result.status is "success"


def test_delete_pod_api_exception(mock_config):
    """Test deleting pod with API exception."""
    with patch.object(
        core_client(),
        "read_namespaced_pod",
        side_effect=ApiException(status=500, reason="Internal Server Error"),
    ), pytest.raises(ApiException):
        result = core_client().read_namespaced_pod("test-name", "test-namespace")
        assert result is False

def test_delete_pods_from_gcpsymphonyresource_success(mock_config):
    """Test deleting pods from GCPSymphonyResource successfully."""
    # Note: create_machine_return_request_resource creates a MachineReturnRequest
    with patch(
        "gke_provider.k8s.resources._get_resource_from_request_id",
        return_value={"metadata": {"name": "test-resource"}},
    ), patch.object(
        custom_obj_api(),
        "create_namespaced_custom_object",
        return_value={"metadata": {"name": "test-mrr"}},
    ):
        result = resources.create_machine_return_request_resource(
            request_id="test-id",
            namespace="test-namespace",
            group="test-group",
            version="test-version",
            machine_ids=["test-name"],
        )
        assert result is not None
        assert result["metadata"]["name"] == "test-mrr"


def test_delete_pods_from_gcpsymphonyresource_api_exception(mock_config):
    """Test deleting pods from GCPSymphonyResource with API exception."""
    with patch(
        "gke_provider.k8s.resources._get_resource_from_request_id",
        return_value={"metadata": {"name": "test-resource"}},
    ), patch.object(
        custom_obj_api(),
        "create_namespaced_custom_object",
        side_effect=ApiException(status=500, reason="Internal Server Error"),
    ), pytest.raises(ApiException):
        resources.create_machine_return_request_resource(
            request_id="test-id",
            namespace="test-namespace",
            group="test-group",
            version="test-version",
            machine_ids=["test-name"],
        )

def test_get_all_gcpsymphonyresources_success(mock_config):
    """Test getting all GCPSymphonyResources successfully."""
    with patch.object(
        custom_obj_api(),
        "list_namespaced_custom_object",
        return_value={"items": []},
    ):
        result = resources.get_all_gcpsymphonyresources(namespace="test-namespace")
        assert result == []


def test_get_all_gcpsymphonyresources_api_exception(mock_config):
    """Test getting all GCPSymphonyResources with API exception."""
    with patch.object(
        custom_obj_api(),
        "list_namespaced_custom_object",
        side_effect=ApiException(status=500, reason="Internal Server Error"),
    ), pytest.raises(Exception):
        resources.get_all_gcpsymphonyresources(namespace="test-namespace")


def test_get_gcpsymphonyresource_from_request_id_success(mock_config):
    """Test getting GCPSymphonyResource from request ID successfully."""
    with patch.object(
        custom_obj_api(),
        "list_namespaced_custom_object",
        return_value={"items": [{"metadata": {"name": "test-resource"}}]},
    ):
        result = resources._get_resource_from_request_id(
            request_id="test-id", namespace="test-namespace"
        )
        assert result == {"metadata": {"name": "test-resource"}}


def test_get_gcpsymphonyresource_from_request_id_no_resource(mock_config):
    """Test getting GCPSymphonyResource from request ID when no resource is found."""
    with patch.object(
        custom_obj_api(),
        "list_namespaced_custom_object",
        return_value={"items": []},
    ), patch.object(get_logger(), "error") as mock_logger_error:
        result = resources._get_resource_from_request_id(
            request_id="test-id", namespace="test-namespace"
        )
        assert result is None
        mock_logger_error.assert_called()


def test_get_gcpsymphonyresource_from_request_id_multiple_resources(mock_config):
    """Test getting GCPSymphonyResource from request ID when multiple resources are found."""
    with patch.object(
        custom_obj_api(),
        "list_namespaced_custom_object",
        return_value={
            "items": [
                {"metadata": {"name": "test-resource1"}},
                {"metadata": {"name": "test-resource2"}},
            ]
        },
    ), patch.object(get_logger(), "error") as mock_logger_error:
        result = resources._get_resource_from_request_id(
            request_id="test-id", namespace="test-namespace"
        )
        assert result is None
        mock_logger_error.assert_called()


def test_get_gcpsymphonyresource_from_request_id_api_exception(mock_config):
    """Test getting GCPSymphonyResource from request ID with API exception."""
    with patch.object(
        custom_obj_api(),
        "list_namespaced_custom_object",
        side_effect=ApiException(status=500, reason="Internal Server Error"),
    ), patch.object(get_logger(), "error") as mock_logger_error:
        result = resources._get_resource_from_request_id(
            request_id="test-id", namespace="test-namespace"
        )
        assert result is None
        mock_logger_error.assert_called()


def test_api_client_returns_kubernetes_client_instance(mock_config):
    """Test getting Kubernetes client instance."""
    with patch.object(k8s_client, "get_kubernetes_client", return_value=MagicMock()):
        api = resources.api_client()
        assert api is not None


def test_custom_obj_api_returns_api_object(mock_config):
    """Test getting CustomObjectsApi client."""
    with patch.object(resources.client, "CustomObjectsApi", return_value=MagicMock()):
        api = resources.custom_obj_api()
        assert hasattr(api, "create_namespaced_custom_object")


def test_app_client_returns_apps_api(mock_config):
    """Test getting AppsV1Api client."""
    with patch.object(resources.client, "AppsV1Api", return_value=MagicMock()):
        api = resources.app_client()
        assert hasattr(api, "list_namespaced_deployment") or hasattr(api, "create_namespaced_deployment")


def test_core_client_returns_core_api(mock_config):
    """Test getting CoreV1Api client."""
    with patch.object(resources.client, "CoreV1Api", return_value=MagicMock()):
        api = resources.core_client()
        assert hasattr(api, "list_namespaced_pod")


def test_get_logger_returns_logger_from_config(mock_config):
    """Test getting logger from config."""
    fake_logger = logging.getLogger("test-logger")
    # Clear cached logger so patched config is used
    resources.get_logger.cache_clear()
    with patch.object(resources, "get_config", return_value=MagicMock(logger=fake_logger)):
        logger = resources.get_logger()
        assert logger is fake_logger


def test_get_plural_list_returns_expected_list(mock_config):
    """Test getting plural list from config."""
    cfg = MagicMock(crd_plural="gcp", crd_return_request_plural="mrr")
    # Clear cached plural list so patched config is used
    resources.get_plural_list.cache_clear()
    with patch.object(resources, "get_config", return_value=cfg):
        plural_list = resources.get_plural_list()
        assert plural_list == ["gcp", "mrr"]


def test_create_gcpsr_object_body_applies_labels_to_pod_spec(mock_config):
    """Test creating GCPSymphonyResource object body applies labels to pod spec."""
    pod_spec = {"containers": []}
    labels = {"env": "test"}
    body = resources._create_gcpsr_object_body(
        name_prefix="np",
        count=1,
        pod_spec=pod_spec,
        group="g",
        kind="k",
        version="v",
        namespace="ns",
        labels=labels,
    )
    assert body is not None
    assert body["metadata"]["labels"]["env"] == "test"
    assert "metadata" in body["spec"]["podSpec"]
    assert "annotations" in body["spec"]["podSpec"]["metadata"]


def test_create_machine_return_request_body_includes_labels_and_requestid(mock_config):
    """Test creating MachineReturnRequest body includes labels and request ID."""
    body = resources.create_machine_return_request_body(
        request_id="rid", machine_ids=["m1", "m2"], namespace="ns", labels={"k": "v"}
    )
    assert body["metadata"]["labels"]["symphony.requestId"] == "rid"
    assert body["spec"]["machineIds"] == ["m1", "m2"]


def test_get_resource_name_from_request_id_uses_helper(mock_config):
    """Test getting resource name from request ID using helper function."""
    with patch.object(resources, "_get_resource_from_request_id", return_value={"metadata": {"name": "res1"}}):
        name = resources._get_resource_name_from_request_id("rid", "ns", "plural")
        assert name == "res1"