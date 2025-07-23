from unittest.mock import AsyncMock, MagicMock, patch

from gcp_symphony_operator.config import Config
from gcp_symphony_operator.handlers.resource_create import (
    resource_create_handler_factory,
)
from kubernetes.client import ApiException, V1ObjectMeta, V1Pod
from typing_extensions import Self


class TestResourceCreateHandler:
    """Tests for the resource_create handler."""

    @patch("gcp_symphony_operator.handlers.resource_create.call_create_pod")
    @patch(
        "gcp_symphony_operator.handlers.resource_create.call_patch_namespaced_custom_object_status"
    )
    async def test_create_gcpsymphonyresource_success(
        self: Self,
        mock_patch_status: AsyncMock,
        mock_create_pod: AsyncMock,
        mock_config: Config,
        mock_logger: MagicMock,
    ) -> None:
        """Test successful creation of a GCPSymphonyResource."""
        # Setup
        mock_config.crd_group = "test-group"
        mock_config.crd_api_version = "v1"
        mock_config.crd_plural = "test-plural"
        mock_config.crd_kind = "TestKind"
        mock_config.default_namespaces = ["test-namespace"]
        mock_config.default_minimum_machine_count = 1
        mock_config.pod_create_batch_size = 1
        mock_config.default_pod_grace_period = 30
        mock_config.operator_name = "test-operator"
        mock_config.request_id_internal_prefix = "int-"

        mock_create_pod.return_value = V1Pod(
            metadata=V1ObjectMeta(name="test-resource-pod-0")
        )

        handler = resource_create_handler_factory(mock_config, mock_logger)

        mock_spec = {
            "machineCount": 1,
            "namePrefix": "test",
            "podSpec": {"containers": [{"name": "test", "image": "test-image"}]},
        }
        mock_meta = {
            "name": "test-resource",
            "namespace": "test-namespace",
            "uid": "test-uid",
            "labels": {"symphony.requestId": "test-request-id"},
        }

        # Call the handler
        await handler(
            spec=mock_spec,
            meta=mock_meta,
            status={},
            logger=mock_logger,
            uid="test-uid",
        )

        # Assertions
        mock_create_pod.assert_called_once()
        mock_patch_status.assert_called_once()
        mock_logger.debug.assert_called()

    @patch("gcp_symphony_operator.handlers.resource_create.call_create_pod")
    @patch(
        "gcp_symphony_operator.handlers.resource_create.call_patch_namespaced_custom_object_status"
    )
    async def test_create_gcpsymphonyresource_pod_creation_failure(
        self: Self,
        mock_patch_status: AsyncMock,
        mock_create_pod: AsyncMock,
        mock_config: Config,
        mock_logger: MagicMock,
    ) -> None:
        """Test handling of pod creation failure."""
        # Setup
        mock_config.crd_group = "test-group"
        mock_config.crd_api_version = "v1"
        mock_config.crd_plural = "test-plural"
        mock_config.crd_kind = "TestKind"
        mock_config.default_namespaces = ["test-namespace"]
        mock_config.default_minimum_machine_count = 1
        mock_config.pod_create_batch_size = 1
        mock_config.default_pod_grace_period = 30
        mock_config.operator_name = "test-operator"
        mock_config.request_id_internal_prefix = "int-"

        mock_create_pod.side_effect = ApiException(
            status=500, reason="Internal Server Error"
        )

        handler = resource_create_handler_factory(mock_config, mock_logger)

        mock_spec = {
            "machineCount": 1,
            "namePrefix": "test",
            "podSpec": {"containers": [{"name": "test", "image": "test-image"}]},
        }
        mock_meta = {
            "name": "test-resource",
            "namespace": "test-namespace",
            "uid": "test-uid",
            "labels": {"symphony.requestId": "test-request-id"},
        }

        # Call the handler
        await handler(
            spec=mock_spec,
            meta=mock_meta,
            status={},
            logger=mock_logger,
            uid="test-uid",
        )

        # Assertions
        mock_create_pod.assert_called_once()
        mock_logger.error.assert_called()
        mock_patch_status.assert_called_once()

    @patch("gcp_symphony_operator.handlers.resource_create.call_create_pod")
    @patch(
        "gcp_symphony_operator.handlers.resource_create.call_patch_namespaced_custom_object_status"
    )
    async def test_create_gcpsymphonyresource_status_update_failure(
        self: Self,
        mock_patch_status: AsyncMock,
        mock_create_pod: AsyncMock,
        mock_config: Config,
        mock_logger: MagicMock,
    ) -> None:
        """Test handling of status update failure."""
        # Setup
        mock_config.crd_group = "test-group"
        mock_config.crd_api_version = "v1"
        mock_config.crd_plural = "test-plural"
        mock_config.crd_kind = "TestKind"
        mock_config.default_namespaces = ["test-namespace"]
        mock_config.default_minimum_machine_count = 1
        mock_config.pod_create_batch_size = 1
        mock_config.default_pod_grace_period = 30
        mock_config.operator_name = "test-operator"
        mock_config.request_id_internal_prefix = "int-"

        mock_create_pod.return_value = V1Pod(
            metadata=V1ObjectMeta(name="test-resource-pod-0")
        )
        mock_patch_status.side_effect = ApiException(
            status=500, reason="Internal Server Error"
        )

        handler = resource_create_handler_factory(mock_config, mock_logger)

        mock_spec = {
            "machineCount": 1,
            "namePrefix": "tet",
            "podSpec": {"containers": [{"name": "test", "image": "test-image"}]},
        }
        mock_meta = {
            "name": "test-resource",
            "namespace": "test-namespace",
            "uid": "test-uid",
            "labels": {"symphony.requestId": "test-request-id"},
        }

        # Call the handler
        await handler(
            spec=mock_spec,
            meta=mock_meta,
            status={},
            logger=mock_logger,
            uid="test-uid",
        )

        # Assertions
        mock_create_pod.assert_called_once()
        mock_patch_status.assert_called_once()
        mock_logger.error.assert_called()

    @patch("gcp_symphony_operator.handlers.resource_create.call_create_pod")
    @patch(
        "gcp_symphony_operator.handlers.resource_create.call_patch_namespaced_custom_object"
    )
    @patch(
        "gcp_symphony_operator.handlers.resource_create.call_patch_namespaced_custom_object_status"
    )
    async def test_create_gcpsymphonyresource_internal_request_id(
        self: Self,
        mock_patch_status: AsyncMock,
        mock_patch_object: AsyncMock,
        mock_create_pod: AsyncMock,
        mock_config: Config,
        mock_logger: MagicMock,
    ) -> None:
        """Test creation with internal request ID generation."""
        # Setup
        mock_config.crd_group = "test-group"
        mock_config.crd_api_version = "v1"
        mock_config.crd_plural = "test-plural"
        mock_config.crd_kind = "TestKind"
        mock_config.default_namespaces = ["test-namespace"]
        mock_config.default_minimum_machine_count = 1
        mock_config.pod_create_batch_size = 1
        mock_config.default_pod_grace_period = 30
        mock_config.operator_name = "test-operator"
        mock_config.request_id_internal_prefix = "int-"

        mock_create_pod.return_value = V1Pod(
            metadata=V1ObjectMeta(name="test-resource-pod-0")
        )

        handler = resource_create_handler_factory(mock_config, mock_logger)

        mock_spec = {
            "machineCount": 1,
            "namePrefix": "test",
            "podSpec": {"containers": [{"name": "test", "image": "test-image"}]},
        }
        mock_meta = {
            "name": "test-resource",
            "namespace": "test-namespace",
            "uid": "test-uid",
            "labels": {},  # No symphony.requestId
        }

        # Call the handler
        await handler(
            spec=mock_spec,
            meta=mock_meta,
            status={},
            logger=mock_logger,
            uid="test-uid",
        )

        # Assertions
        mock_create_pod.assert_called_once()
        mock_patch_status.assert_called_once()
        mock_patch_object.assert_called_once()  # Should patch metadata with internal request ID
        mock_logger.warning.assert_called()  # Should warn about missing request ID
