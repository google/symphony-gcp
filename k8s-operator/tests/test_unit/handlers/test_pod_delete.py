"""
Unit tests for the handlers/pod_delete.py module.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import kopf
import pytest
from gcp_symphony_operator.config import Config
from gcp_symphony_operator.handlers.pod_delete import pod_delete_handler_factory
from kubernetes.client import ApiException
from typing_extensions import Self


class TestPodDeleteHandler:
    """Tests for the pod_delete_handler."""

    @patch("gcp_symphony_operator.handlers.pod_delete.call_get_custom_object")
    @patch("gcp_symphony_operator.handlers.pod_delete.enqueue_status_update")
    async def test_pod_delete_handler_success(
        self: Self,
        mock_enqueue: AsyncMock,
        mock_get_custom_object: AsyncMock,
        mock_config: Config,
        mock_logger: MagicMock,
    ) -> None:
        """Test successful pod deletion handling."""
        # Setup
        mock_config.operator_name = "test-operator"
        mock_config.crd_plural = "test-plural"
        mock_config.crd_kind = "TestKind"
        mock_config.crd_finalizer = "test-finalizer"

        handler = pod_delete_handler_factory(mock_config, mock_logger)
        assert handler is not None, "Handler should not be None"

        mock_get_custom_object.return_value = {
            "metadata": {"resourceVersion": "123"},
            "status": {"returnedMachines": []},
        }

        mock_meta = {
            "name": "test-pod",
            "namespace": "test-namespace",
            "labels": {
                "app": "test-owner",
                "managed-by": "test-operator",
                "symphony.requestId": "test-request-id",
                "symphony.returnRequestId": "test-return-id",
            },
        }

        # Call the handler
        await handler(
            meta=mock_meta,
            spec=None,
            status=None,
            old=None,
            new=None,
            logger=mock_logger,
        )

        # Assertions
        mock_get_custom_object.assert_called_once()
        mock_enqueue.assert_called_once()
        mock_logger.info.assert_called()

    @patch("gcp_symphony_operator.handlers.pod_delete.call_get_custom_object")
    async def test_pod_delete_handler_owner_not_found(
        self: Self,
        mock_get_custom_object: AsyncMock,
        mock_config: Config,
        mock_logger: MagicMock,
    ) -> None:
        """Test handling when the owner resource is not found."""
        # Setup
        mock_config.operator_name = "test-operator"
        mock_config.crd_plural = "test-plural"
        mock_config.crd_kind = "TestKind"
        mock_config.crd_finalizer = "test-finalizer"

        handler = pod_delete_handler_factory(mock_config, mock_logger)
        mock_get_custom_object.side_effect = ApiException(
            status=404, reason="Not Found"
        )

        mock_meta = {
            "name": "test-pod",
            "namespace": "test-namespace",
            "labels": {
                "app": "test-owner",
                "managed-by": "test-operator",
                "symphony.requestId": "test-request-id",
            },
            "finalizers": [],
        }

        # Call the handler
        with pytest.raises(ApiException) as exc_info:
            await handler(
                meta=mock_meta,
                spec=None,
                status=None,
                old=None,
                new=None,
                logger=mock_logger,
            )

        # Verify the error message
        assert "Owner resource test-owner of kind TestKind not found" in str(
            exc_info.value
        )

        # Assertions
        mock_get_custom_object.assert_called_once()
        mock_logger.warning.assert_called()

    async def test_pod_delete_handler_no_owner(
        self: Self,
        mock_config: Config,
        mock_logger: MagicMock,
    ) -> None:
        """Test handling of missing owner reference."""
        # Setup
        mock_config.operator_name = "test-operator"
        mock_config.crd_plural = "test-plural"
        mock_config.crd_kind = "TestKind"

        handler = pod_delete_handler_factory(mock_config, mock_logger)

        mock_meta = {
            "name": "test-pod",
            "namespace": "test-namespace",
            "labels": {
                "managed-by": "test-operator",
                # No 'app' label (owner reference)
            },
        }

        # Call the handler
        await handler(
            meta=mock_meta,
            spec=None,
            status=None,
            old=None,
            new=None,
            logger=mock_logger,
        )

        # Assertions
        mock_logger.error.assert_called_with("Pod test-pod has no owner reference")

    async def test_pod_delete_handler_no_request_id(
        self: Self,
        mock_config: Config,
        mock_logger: MagicMock,
    ) -> None:
        """Test handling of missing request ID."""
        # Setup
        mock_config.operator_name = "test-operator"
        mock_config.crd_plural = "test-plural"
        mock_config.crd_kind = "TestKind"

        handler = pod_delete_handler_factory(mock_config, mock_logger)

        mock_meta = {
            "name": "test-pod",
            "namespace": "test-namespace",
            "labels": {
                "app": "test-owner",
                "managed-by": "test-operator",
                # No symphony.requestId label
            },
        }

        # Call the handler and expect TemporaryError
        with pytest.raises(kopf.TemporaryError):
            await handler(
                meta=mock_meta,
                spec=None,
                status=None,
                old=None,
                new=None,
                logger=mock_logger,
            )

        # Assertions
        mock_logger.error.assert_called_with("Pod test-pod has no request ID label")

    async def test_pod_delete_handler_no_request_id_raises_temporary_error(
        self: Self,
        mock_config: Config,
        mock_logger: MagicMock,
    ) -> None:
        """Test handling of missing request ID label raises TemporaryError."""
        # Setup
        mock_config.operator_name = "test-operator"
        mock_config.crd_plural = "test-plural"
        mock_config.crd_kind = "TestKind"

        handler = pod_delete_handler_factory(mock_config, mock_logger)

        mock_meta = {
            "name": "test-pod",
            "namespace": "test-namespace",
            "labels": {
                "managed-by": "test-operator",
                "app": "test-owner",
                # No symphony.requestId label
            },
        }

        # Call the handler and expect TemporaryError
        with pytest.raises(kopf.TemporaryError):
            await handler(
                meta=mock_meta,
                spec=None,
                status=None,
                old=None,
                new=None,
                logger=mock_logger,
            )

        # Assertions
        mock_logger.error.assert_called_with("Pod test-pod has no request ID label")
