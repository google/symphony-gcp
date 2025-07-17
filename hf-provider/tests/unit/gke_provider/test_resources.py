import gke_provider.k8s.resources as resources
from unittest.mock import patch, MagicMock
import pytest
from kubernetes.client.rest import ApiException
from kubernetes.client.models import V1Pod

from gke_provider.k8s.resources import custom_obj_api, core_client, get_logger


def test_get_pod_from_hostname_success(mock_config):
    """Test getting pod from hostname successfully."""
    with patch.object(
        core_client(),
        "read_namespaced_pod",
        return_value=V1Pod(),
    ):
        result = resources.get_pod_from_hostname("test-name", "test-namespace")
        assert result is not None


def test_get_pod_from_hostname_invalid_name(mock_config):
    """Test getting pod from hostname with invalid name."""
    result = resources.get_pod_from_hostname("test", "test-namespace")
    assert result is None


def test_get_pod_from_hostname_invalid_namespace(mock_config):
    """Test getting pod from hostname with invalid namespace."""
    with patch.object(
        core_client(),
        "read_namespaced_pod",
        return_value=None,
    ):
        result = resources.get_pod_from_hostname("test-name", "test")
        assert result is None


def test_get_pod_from_hostname_api_exception(mock_config):
    """Test getting pod from hostname with API exception."""
    with patch.object(
        core_client(),
        "read_namespaced_pod",
        side_effect=ApiException(status=404, reason="Not Found"),
    ):
        result = resources.get_pod_from_hostname("test-name", "test-namespace")
        assert result is None


def test_create_gcpsymphonyresource_success(mock_config):
    """Test creating GCPSymphonyResource successfully."""
    with patch.object(
        custom_obj_api(),
        "list_namespaced_custom_object",
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
    with patch.object(
        custom_obj_api(),
        "list_namespaced_custom_object",
        return_value=MagicMock(),
    ) as mock_get_namespaced_custom_object:
        result = resources.get_gcpsymphonyresource(
            name="test-name",
            namespace="test-namespace",
            group="test-group",
            kind="test-kind",
        )
        assert result is not None
        mock_get_namespaced_custom_object.assert_called_once()


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
        result = resources.get_gcpsymphonyresource(
            name="test-name",
            namespace="test-namespace",
            group="test-group",
            kind="test-kind",
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
    ) as mock_logger_info:
        result = resources.get_gcpsymphonyresource(
            name="test-name",
            namespace="test-namespace",
            group="test-group",
            kind="test-kind",
            ignore_not_found=True,
        )
        assert result is None
        mock_get_namespaced_custom_object.assert_called_once()
        mock_logger_info.assert_called()


def test_delete_gcpsymphonyresource_success(mock_config):
    """Test deleting GCPSymphonyResource successfully."""
    with patch.object(
        custom_obj_api(),
        "list_namespaced_custom_object",
    ) as mock_delete_namespaced_custom_object:
        mock_delete_namespaced_custom_object.return_value = MagicMock()
        result = resources.delete_gcpsymphonyresource(
            name="test-name",
            namespace="test-namespace",
            group="test-group",
            kind="test-kind",
        )
        assert result is not None


def test_delete_gcpsymphonyresource_api_exception(mock_config):
    """Test deleting GCPSymphonyResource with API exception."""
    with patch.object(
        custom_obj_api(),
        "list_namespaced_custom_object",
        side_effect=ApiException(status=500, reason="Internal Server Error"),
    ), pytest.raises(Exception):
        resources.delete_gcpsymphonyresource(
            name="test-name",
            namespace="test-namespace",
            group="test-group",
            kind="test-kind",
        )


def test_delete_pod_success(mock_config):
    """Test deleting pod successfully."""
    with patch.object(
        core_client(),
        "delete_namespaced_pod",
        return_value=MagicMock(),
    ):
        result = resources.delete_pod(name="test-name", namespace="test-namespace")
        assert result is True


def test_delete_pod_api_exception(mock_config):
    """Test deleting pod with API exception."""
    with patch.object(
        core_client(),
        "delete_namespaced_pod",
        side_effect=ApiException(status=500, reason="Internal Server Error"),
    ):
        result = resources.delete_pod(name="test-name", namespace="test-namespace")
        assert result is False


def test_delete_pods_success(mock_config):
    """Test deleting pods successfully."""
    with patch(
        "gke_provider.k8s.resources.get_pod_from_hostname", return_value=MagicMock()
    ), patch.object(
        core_client(),
        "patch_namespaced_pod",
        return_value=MagicMock(),
    ), patch(
        "gke_provider.k8s.resources.delete_pod", return_value=True
    ):
        success, failed = resources.delete_pods(
            pod_list=["test-name"],
            deleteRequestId="test-id",
            namespace="test-namespace",
        )
        assert len(success) == 1
        assert len(failed) == 0


def test_delete_pods_api_exception(mock_config):
    """Test deleting pods with API exception."""
    with patch(
        "gke_provider.k8s.resources.get_pod_from_hostname", return_value=MagicMock()
    ), patch.object(
        core_client(),
        "patch_namespaced_pod",
        side_effect=ApiException(status=500, reason="Internal Server Error"),
    ), patch(
        "gke_provider.k8s.resources.delete_pod", return_value=True
    ):
        success, failed = resources.delete_pods(
            pod_list=["test-name"],
            deleteRequestId="test-id",
            namespace="test-namespace",
        )
        assert len(success) == 0
        assert len(failed) == 1


def test_delete_pods_from_gcpsymphonyresource_success(mock_config):
    """Test deleting pods from GCPSymphonyResource successfully."""
    with patch(
        "gke_provider.k8s.resources._get_gcpsymphonyresource_from_request_id",
        return_value={"metadata": {"name": "test-resource"}},
    ), patch.object(
        custom_obj_api(),
        "list_namespaced_custom_object",
        return_value=MagicMock(),
    ):
        result = resources.delete_pods_from_gcpsymphonyresource(
            request_id="test-id",
            namespace="test-namespace",
            group="test-group",
            version="test-version",
            pod_names=["test-name"],
        )
        assert result is True


def test_delete_pods_from_gcpsymphonyresource_api_exception(mock_config):
    """Test deleting pods from GCPSymphonyResource with API exception."""
    with patch(
        "gke_provider.k8s.resources._get_gcpsymphonyresource_from_request_id",
        return_value={"metadata": {"name": "test-resource"}},
    ), patch.object(
        custom_obj_api(),
        "list_namespaced_custom_object",
        side_effect=ApiException(status=500, reason="Internal Server Error"),
    ):
        result = resources.delete_pods_from_gcpsymphonyresource(
            request_id="test-id",
            namespace="test-namespace",
            group="test-group",
            version="test-version",
            pod_names=["test-name"],
        )
        assert result is False


def test_get_resource_and_pod_status_success(mock_config):
    """Test getting resource and pod status successfully."""
    with patch(
        "gke_provider.k8s.resources._get_gcpsr_name_from_request_id",
        return_value="test-resource",
    ), patch.object(
        core_client(),
        "list_namespaced_pod",
        return_value=MagicMock(),
    ), patch(
        "gke_provider.k8s.resources.get_gcpsymphonyresource_phase",
        return_value=("Running", 2),
    ):
        result = resources.get_resource_and_pod_status(
            requestId="test-id", namespace="test-namespace"
        )
        assert result is not None


def test_get_resource_and_pod_status_api_exception(mock_config):
    """Test getting resource and pod status with API exception."""
    with patch(
        "gke_provider.k8s.resources._get_gcpsr_name_from_request_id",
        return_value="test-resource",
    ), patch.object(
        core_client(),
        "list_namespaced_pod",
        side_effect=ApiException(status=500, reason="Internal Server Error"),
    ), pytest.raises(
        Exception
    ):
        resources.get_resource_and_pod_status(
            requestId="test-id", namespace="test-namespace"
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


def test_get_pods_success(mock_config):
    """Test getting pods successfully."""
    with patch(
        "gke_provider.k8s.resources.get_pod_from_hostname", return_value={"test": "pod"}
    ):
        result = resources.get_pods(pod_list=["test-pod"], namespace="test-namespace")
        assert result == [{"test": "pod"}]


def test_get_pods_no_pods(mock_config):
    """Test getting pods with no pods."""
    result = resources.get_pods(pod_list=[], namespace="test-namespace")
    assert result == []


def test_delete_pods_pod_not_found(mock_config):
    """Test deleting pods when a pod is not found."""
    with patch.object(
        custom_obj_api(), "list_namespaced_custom_object", return_value=None
    ), patch.object(core_client(), "patch_namespaced_pod"), patch(
        "gke_provider.k8s.resources.delete_pod"
    ):
        success, failed = resources.delete_pods(
            pod_list=["test-name"],
            deleteRequestId="test-id",
            namespace="test-namespace",
        )
        assert len(success) == 0
        assert len(failed) == 1


def test_delete_pods_delete_pod_fails(mock_config):
    """Test deleting pods when delete_pod fails."""
    with patch.object(
        custom_obj_api(), "list_namespaced_custom_object", return_value=MagicMock()
    ), patch.object(
        core_client(),
        "patch_namespaced_pod",
        return_value=MagicMock(),
    ), patch(
        "gke_provider.k8s.resources.delete_pod", return_value=False
    ):
        success, failed = resources.delete_pods(
            pod_list=["test-name"],
            deleteRequestId="test-id",
            namespace="test-namespace",
        )
        assert len(success) == 0
        assert len(failed) == 1


def test_get_gcpsymphonyresource_from_request_id_success(mock_config):
    """Test getting GCPSymphonyResource from request ID successfully."""
    with patch.object(
        custom_obj_api(),
        "list_namespaced_custom_object",
        return_value={"items": [{"metadata": {"name": "test-resource"}}]},
    ):
        result = resources._get_gcpsymphonyresource_from_request_id(
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
        result = resources._get_gcpsymphonyresource_from_request_id(
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
        result = resources._get_gcpsymphonyresource_from_request_id(
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
        result = resources._get_gcpsymphonyresource_from_request_id(
            request_id="test-id", namespace="test-namespace"
        )
        assert result is None
        mock_logger_error.assert_called()
