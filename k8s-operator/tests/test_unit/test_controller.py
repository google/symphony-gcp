"""
Unit tests for the controller.py module.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src"))
)
from gcp_symphony_operator.config import Config  # noqa: E402
from gcp_symphony_operator.controller import (  # noqa: E402
    kopf_cleanup,
    kopf_startup,
    run_operator,
)
from typing_extensions import Self  # noqa: E402


class TestKopfStartup:
    """Tests for the kopf_startup function."""

    @pytest.mark.asyncio
    @patch("gcp_symphony_operator.controller.get_config")
    @patch("gcp_symphony_operator.controller.get_op_context")
    @patch("gcp_symphony_operator.controller.set_op_context")
    @patch("gcp_symphony_operator.controller.get_cleanup_worker")
    @patch("gcp_symphony_operator.controller.set_cleanup_worker")
    async def test_kopf_startup_success(
        self: Self,
        mock_set_cleanup_worker: MagicMock,
        mock_get_cleanup_worker: MagicMock,
        mock_set_op_context: MagicMock,
        mock_get_op_context: MagicMock,
        mock_get_config: AsyncMock,
    ) -> None:
        """Test successful kopf startup."""
        # Setup
        mock_config = MagicMock()
        mock_config.kopf_posting_enabled = True
        mock_config.crd_finalizer = "symphony-operator/finalizer"
        mock_config.kopf_max_workers = 20
        mock_config.kopf_server_timeout = 300
        mock_config.health_check_enabled = False
        mock_get_config.return_value = mock_config

        mock_context = MagicMock()
        mock_context.start_update_worker = AsyncMock()
        mock_get_op_context.return_value = mock_context

        mock_cleanup_worker = MagicMock()
        mock_cleanup_worker.start = AsyncMock()
        mock_get_cleanup_worker.return_value = mock_cleanup_worker

        mock_settings = MagicMock()

        # Call the function
        await kopf_startup(settings=mock_settings)  # type: ignore[call-arg]

        # Assertions
        mock_get_config.assert_called_once()
        mock_context.start_update_worker.assert_called_once()
        mock_cleanup_worker.start.assert_called_once()
        mock_context.set_ready.assert_called_with(True)
        assert mock_settings.posting.enabled is True
        assert mock_settings.persistence.finalizer == "symphony-operator/finalizer"
        assert mock_settings.batching.error_delays == [10, 20, 30]


class TestRunOperator:
    """Tests for the run_operator function."""

    @patch("gcp_symphony_operator.controller.OperatorContext")
    @patch("gcp_symphony_operator.controller.set_op_context")
    @patch("gcp_symphony_operator.controller.kopf.run")
    @patch("sys.argv")
    def test_run_operator_success(
        self: Self,
        mock_argv: MagicMock,
        mock_kopf_run: MagicMock,
        mock_set_op_context: MagicMock,
        mock_operator_context: MagicMock,
        mock_config: Config,
        mock_logger: MagicMock,
    ) -> None:
        """Test successful operator run."""
        # Setup
        mock_context = MagicMock()
        mock_context.update_queue = MagicMock()
        mock_context.stop_event = MagicMock()
        mock_operator_context.return_value = mock_context
        mock_config.operator_version = "1.0.0"
        mock_config.kopf_server_timeout = 300
        mock_config.kopf_max_workers = 20
        mock_config.default_namespaces = ["test-namespace"]

        # Call the function
        run_operator(mock_config, mock_logger)

        # Assertions
        mock_operator_context.assert_called_once_with(mock_config)
        mock_context.initialize_queue.assert_called_once()
        mock_set_op_context.assert_called_once_with(mock_context)
        mock_kopf_run.assert_called_once_with(
            namespaces=mock_config.default_namespaces, standalone=True
        )
        mock_logger.info.assert_any_call(
            f"Starting GCP Symphony Operator v{mock_config.operator_version}"
        )

    @patch("gcp_symphony_operator.controller.OperatorContext")
    def test_run_operator_queue_not_initialized(
        self: Self,
        mock_operator_context: MagicMock,
        mock_config: Config,
        mock_logger: MagicMock,
    ) -> None:
        """Test operator run when queue is not initialized."""
        # Setup
        mock_context = MagicMock()
        mock_context.update_queue = None
        mock_context.stop_event = None
        mock_operator_context.return_value = mock_context

        # Call the function and expect exception
        with pytest.raises(RuntimeError, match="Queue not initialized"):
            run_operator(mock_config, mock_logger)


class TestKopfCleanup:
    """Tests for the kopf_cleanup function."""

    @pytest.mark.asyncio
    @patch("gcp_symphony_operator.controller.get_config")
    @patch("gcp_symphony_operator.controller.get_op_context")
    @patch("gcp_symphony_operator.controller.get_cleanup_worker")
    async def test_kopf_cleanup_success(
        self: Self,
        mock_get_cleanup_worker: MagicMock,
        mock_get_op_context: MagicMock,
        mock_get_config: AsyncMock,
    ) -> None:
        """Test successful kopf cleanup."""
        # Setup
        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        mock_context = MagicMock()
        mock_context.stop_update_worker = AsyncMock()
        mock_get_op_context.return_value = mock_context

        mock_cleanup_worker = MagicMock()
        mock_cleanup_worker.stop = AsyncMock()
        mock_get_cleanup_worker.return_value = mock_cleanup_worker

        # Call the function
        await kopf_cleanup()  # type: ignore[call-arg]

        # Assertions
        mock_context.set_ready.assert_called_with(False)
        mock_context.stop_update_worker.assert_called_once()
        mock_cleanup_worker.stop.assert_called_once()
