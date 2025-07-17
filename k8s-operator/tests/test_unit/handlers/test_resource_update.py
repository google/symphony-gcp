from logging import Logger
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from gcp_symphony_operator.config import Config
from gcp_symphony_operator.handlers.resource_update import (
    resource_update_handler_factory,
)
from kubernetes.client import ApiException, V1ObjectMeta, V1Pod, V1PodList
from tests.conftest import MockLogger


@pytest.fixture
def handler(mock_config: Config, mock_logger: Logger) -> Any:
    """Fixture for the resource update handler."""
    return resource_update_handler_factory(mock_config, mock_logger)


@patch("gcp_symphony_operator.handlers.resource_update.call_list_namespaced_pod")
@patch(
    "gcp_symphony_operator.handlers.resource_update.call_patch_namespaced_custom_object_status"
)
@pytest.mark.asyncio
async def test_update_gcpsymphonyresource_when_no_machines_mark_resource_completed(
    mock_patch_status: MagicMock,
    mock_list_pods: MagicMock,
    mock_config: Config,
    mock_logger: MockLogger,
    handler: Any,
) -> None:
    """
    Test that the resource is marked completed when availableMachines becomes
    0 and no pods exist.
    """
    # Mock empty pod list
    mock_list_pods.return_value = V1PodList(items=[])

    new_val = 0
    old_val = 1
    spec: Dict[str, Any] = {}
    meta = {
        "name": "test-resource",
        "namespace": "test-namespace",
        "resourceVersion": "1",
        "labels": {"symphony.requestId": "test-request-123"},
    }
    status = {"availableMachines": 1}

    await handler(
        new=new_val,
        old=old_val,
        spec=spec,
        meta=meta,
        status=status,
        logger=mock_logger,
    )

    # Assert that patch status was called to mark as completed
    mock_patch_status.assert_called_once()
    mock_list_pods.assert_called_once_with(
        namespace="test-namespace", label_selector="symphony.requestId=test-request-123"
    )


@patch("gcp_symphony_operator.handlers.resource_update.call_list_namespaced_pod")
@patch(
    "gcp_symphony_operator.handlers.resource_update.call_patch_namespaced_custom_object_status"
)
@pytest.mark.asyncio
async def test_update_gcpsymphonyresource_when_no_machines_skip_delete_with_pods(
    mock_patch_status: MagicMock,
    mock_list_pods: MagicMock,
    mock_config: Config,
    mock_logger: MockLogger,
    handler: Any,
) -> None:
    """
    Test that the resource is not marked completed when availableMachines
    becomes 0 but pods exist.
    """
    # Mock pod list with one active pod
    pod = V1Pod(metadata=V1ObjectMeta(deletion_timestamp=None))
    mock_list_pods.return_value = V1PodList(items=[pod])

    new_val = 0
    old_val = 1
    spec: Dict[str, Any] = {}
    meta = {
        "name": "test-resource",
        "namespace": "test-namespace",
        "resourceVersion": "1",
        "labels": {"symphony.requestId": "test-request-123"},
    }
    status = {"availableMachines": 1}

    await handler(
        new=new_val,
        old=old_val,
        spec=spec,
        meta=meta,
        status=status,
        logger=mock_logger,
    )

    # Assert that patch status was not called
    mock_patch_status.assert_not_called()


@patch("gcp_symphony_operator.handlers.resource_update.call_list_namespaced_pod")
@patch(
    "gcp_symphony_operator.handlers.resource_update.call_patch_namespaced_custom_object_status"
)
@pytest.mark.asyncio
async def test_update_gcpsymphonyresource_when_no_machines_skip_delete_with_pods_marked_for_deletion(  # noqa: E501
    mock_patch_status: MagicMock,
    mock_list_pods: MagicMock,
    mock_config: Config,
    mock_logger: MockLogger,
    handler: Any,
) -> None:
    """
    Test that the resource is marked completed when availableMachines becomes 0 and
    pods exist but are marked for deletion.
    """
    # Mock pod list with one pod marked for deletion
    pod = V1Pod(metadata=V1ObjectMeta(deletion_timestamp="2024-01-01T00:00:00Z"))
    mock_list_pods.return_value = V1PodList(items=[pod])

    new_val = 0
    old_val = 1
    spec: Dict[str, Any] = {}
    meta = {
        "name": "test-resource",
        "namespace": "test-namespace",
        "resourceVersion": "1",
        "labels": {"symphony.requestId": "test-request-123"},
    }
    status = {"availableMachines": 1}

    await handler(
        new=new_val,
        old=old_val,
        spec=spec,
        meta=meta,
        status=status,
        logger=mock_logger,
    )

    # Assert that patch status was called
    mock_patch_status.assert_called_once()


@patch("gcp_symphony_operator.handlers.resource_update.call_list_namespaced_pod")
@patch(
    "gcp_symphony_operator.handlers.resource_update.call_patch_namespaced_custom_object_status"
)
@pytest.mark.asyncio
async def test_update_gcpsymphonyresource_when_no_machines_api_exception(
    mock_patch_status: MagicMock,
    mock_list_pods: MagicMock,
    mock_config: Config,
    mock_logger: MockLogger,
    handler: Any,
) -> None:
    """Test that the handler handles an ApiException when patching the resource status."""
    # Mock empty pod list
    mock_list_pods.return_value = V1PodList(items=[])

    # Mock patch status to raise an ApiException
    mock_patch_status.side_effect = ApiException(
        status=500, reason="Internal Server Error"
    )

    new_val = 0
    old_val = 1
    spec: Dict[str, Any] = {}
    meta = {
        "name": "test-resource",
        "namespace": "test-namespace",
        "resourceVersion": "1",
        "labels": {"symphony.requestId": "test-request-123"},
    }
    status = {"availableMachines": 1}

    await handler(
        new=new_val,
        old=old_val,
        spec=spec,
        meta=meta,
        status=status,
        logger=mock_logger,
    )

    # Assert that patch status was called
    mock_patch_status.assert_called_once()
    # Assert that logger.error was called
    mock_logger.error.assert_called()


@patch("gcp_symphony_operator.handlers.resource_update.call_list_namespaced_pod")
@patch(
    "gcp_symphony_operator.handlers.resource_update.call_patch_namespaced_custom_object_status"
)
@pytest.mark.asyncio
async def test_update_gcpsymphonyresource_when_no_machines_resource_not_found(
    mock_patch_status: MagicMock,
    mock_list_pods: MagicMock,
    mock_config: Config,
    mock_logger: MockLogger,
    handler: Any,
) -> None:
    """Test that the handler handles a 404 ApiException when patching the resource status."""
    # Mock empty pod list
    mock_list_pods.return_value = V1PodList(items=[])

    # Mock patch status to raise a 404 ApiException
    mock_patch_status.side_effect = ApiException(status=404, reason="Not Found")

    new_val = 0
    old_val = 1
    spec: Dict[str, Any] = {}
    meta = {
        "name": "test-resource",
        "namespace": "test-namespace",
        "resourceVersion": "1",
        "labels": {"symphony.requestId": "test-request-123"},
    }
    status = {"availableMachines": 1}

    await handler(
        new=new_val,
        old=old_val,
        spec=spec,
        meta=meta,
        status=status,
        logger=mock_logger,
    )

    # Assert that patch status was called
    mock_patch_status.assert_called_once()
    # Assert that logger.warning was called
    mock_logger.warning.assert_called()


@patch("gcp_symphony_operator.handlers.resource_update.call_list_namespaced_pod")
@pytest.mark.asyncio
async def test_update_gcpsymphonyresource_when_no_machines_early_return(
    mock_list_pods: MagicMock,
    mock_config: Config,
    mock_logger: MockLogger,
    handler: Any,
) -> None:
    """Test that the handler returns early if conditions are not met."""

    new_val = 1
    old_val = 0
    spec: Dict[str, Any] = {}
    meta = {
        "name": "test-resource",
        "namespace": "test-namespace",
        "resourceVersion": "1",
    }
    status = {"availableMachines": 1}

    await handler(
        new=new_val,
        old=old_val,
        spec=spec,
        meta=meta,
        status=status,
        logger=mock_logger,
    )

    # Assert that list_pods was not called (early return occurred)
    mock_list_pods.assert_not_called()
