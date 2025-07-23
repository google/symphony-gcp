from unittest.mock import AsyncMock, MagicMock, patch

from gcp_symphony_operator.config import Config
from gcp_symphony_operator.handlers.container_state_change import (
    container_state_handler_factory,
)
from kubernetes.client import ApiException
from typing_extensions import Self


class TestContainerStateHandler:
    """Tests for the container_state_handler."""

    @patch(
        "gcp_symphony_operator.handlers.container_state_change.call_get_custom_object"
    )
    @patch(
        "gcp_symphony_operator.handlers.container_state_change.enqueue_status_update"
    )
    async def test_container_state_handler_success(
        self: Self,
        mock_enqueue_status_update: AsyncMock,
        mock_get_custom_object: AsyncMock,
        mock_config: Config,
        mock_logger: MagicMock,
    ) -> None:
        """Test successful container state handling."""
        # Setup
        mock_config.operator_name = "test-operator"
        mock_config.crd_kind = "TestKind"
        mock_config.crd_group = "test-group"
        mock_config.crd_api_version = "v1"
        mock_config.crd_plural = "test-plural"
        mock_config.default_namespaces = ["test-namespace"]

        mock_get_custom_object.return_value = {
            "metadata": {"name": "test-resource"},
            "spec": {
                "podSpec": {"containers": [{"name": "test", "image": "test:latest"}]},
                "namePrefix": "test-pod",
                "machineCount": 1,
            },
            "status": {"phase": "Running", "availableMachines": 1},
        }

        handler = container_state_handler_factory(mock_config, mock_logger)

        mock_meta = {
            "name": "test-pod",
            "namespace": "test-namespace",
            "labels": {
                "managed-by": "test-operator",
                "symphony.requestId": "test-request-id",
            },
            "ownerReferences": [
                {
                    "kind": "TestKind",
                    "apiVersion": "test-group/v1",
                    "name": "test-resource",
                }
            ],
        }

        new_container_statuses = [
            {
                "name": "test-container",
                "ready": True,
                "state": {"running": {}},
            }
        ]

        old_container_status = [
            {
                "name": "test-container",
                "ready": False,
                "state": {"waiting": {"reason": "ContainerCreating"}},
            }
        ]

        # Call the handler
        await handler(
            meta=mock_meta,
            spec=None,
            status={"phase": "Running"},
            old=old_container_status,
            new=new_container_statuses,
            logger=mock_logger,
        )

        # Assertions
        mock_get_custom_object.assert_called_once()
        mock_enqueue_status_update.assert_called_once()
        mock_logger.info.assert_called()

    @patch(
        "gcp_symphony_operator.handlers.container_state_change.call_get_custom_object"
    )
    async def test_container_state_handler_owner_not_found(
        self: Self,
        mock_get_custom_object: AsyncMock,
        mock_config: Config,
        mock_logger: MagicMock,
    ) -> None:
        """Test handling when the owner resource is not found."""
        # Setup
        mock_config.operator_name = "test-operator"
        mock_config.crd_kind = "TestKind"
        mock_config.crd_group = "test-group"
        mock_config.crd_api_version = "v1"
        mock_config.crd_plural = "test-plural"

        mock_get_custom_object.side_effect = ApiException(
            status=404, reason="Not Found"
        )
        handler = container_state_handler_factory(mock_config, mock_logger)

        mock_meta = {
            "name": "test-pod",
            "namespace": "test-namespace",
            "labels": {
                "managed-by": "test-operator",
                "symphony.requestId": "test-request-id",
            },
            "ownerReferences": [
                {
                    "kind": "TestKind",
                    "apiVersion": "test-group/v1",
                    "name": "test-resource",
                }
            ],
        }

        new_container_statuses = [
            {
                "name": "test-container",
                "ready": True,
                "state": {"running": {}},
            }
        ]

        # Call the handler
        await handler(
            meta=mock_meta,
            spec=None,
            status={"phase": "Running"},
            old=None,
            new=new_container_statuses,
            logger=mock_logger,
        )

        # Assertions
        mock_get_custom_object.assert_called_once()
        mock_logger.error.assert_called()

    async def test_container_state_handler_no_owner(
        self: Self,
        mock_config: Config,
        mock_logger: MagicMock,
    ) -> None:
        """Test handling of missing owner reference."""
        # Setup
        mock_config.operator_name = "test-operator"
        mock_config.crd_kind = "TestKind"

        handler = container_state_handler_factory(mock_config, mock_logger)

        mock_meta = {
            "name": "test-pod",
            "namespace": "test-namespace",
            "labels": {
                "managed-by": "test-operator",
                "symphony.requestId": "test-request-id",
            },
            "ownerReferences": [],  # No owner references
        }

        new_container_statuses = [
            {
                "name": "test-container",
                "ready": True,
                "state": {"running": {}},
            }
        ]

        # Call the handler
        await handler(
            meta=mock_meta,
            spec=None,
            status={"phase": "Running"},
            old=None,
            new=new_container_statuses,
            logger=mock_logger,
        )

        # Assertions
        mock_logger.error.assert_called_with("Pod test-pod has no owner references")

    async def test_container_state_handler_no_request_id(
        self: Self,
        mock_config: Config,
        mock_logger: MagicMock,
    ) -> None:
        """Test handling of missing request ID label."""
        # Setup
        mock_config.operator_name = "test-operator"

        handler = container_state_handler_factory(mock_config, mock_logger)

        mock_meta = {
            "name": "test-pod",
            "namespace": "test-namespace",
            "labels": {
                "managed-by": "test-operator",
                # No symphony.requestId label
            },
        }

        new_container_statuses = [
            {
                "name": "test-container",
                "ready": True,
                "state": {"running": {}},
            }
        ]

        # Call the handler
        await handler(
            meta=mock_meta,
            spec=None,
            status={"phase": "Running"},
            old=None,
            new=new_container_statuses,
            logger=mock_logger,
        )

        # Assertions
        mock_logger.error.assert_called_with("Pod test-pod has no requestId label")

    async def test_container_state_handler_no_container_status(
        self: Self,
        mock_config: Config,
        mock_logger: MagicMock,
    ) -> None:
        """Test handling when no container status is provided."""
        # Setup
        mock_config.operator_name = "test-operator"

        handler = container_state_handler_factory(mock_config, mock_logger)

        mock_meta = {
            "name": "test-pod",
            "namespace": "test-namespace",
            "labels": {
                "managed-by": "test-operator",
                "symphony.requestId": "test-request-id",
            },
        }

        # Call the handler with no new container statuses
        await handler(
            meta=mock_meta,
            spec=None,
            status={"phase": "Running"},
            old=None,
            new=None,  # No container statuses
            logger=mock_logger,
        )

        # Assertions
        mock_logger.debug.assert_called_with("Pod test-pod has no new container status")
