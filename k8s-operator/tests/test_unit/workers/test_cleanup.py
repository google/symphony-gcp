from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from gcp_symphony_operator.config import Config
from gcp_symphony_operator.workers.cleanup import CleanupWorker
from kubernetes.client import ApiException
from typing_extensions import Self


class TestCleanupWorker:
    def test_cleanup_worker_init(self: Self, mock_config: Config) -> None:
        """Test CleanupWorker initialization."""
        mock_config._Config__initialized = True
        worker = CleanupWorker(mock_config)
        assert worker.config == mock_config
        assert worker.logger == mock_config.logger

    def test_cleanup_worker_init_config_not_initialized(
        self: Self, mock_config: Config
    ) -> None:
        """Test CleanupWorker initialization with uninitialized config."""
        mock_config._Config__initialized = False
        with pytest.raises(
            RuntimeError, match="Config object not properly initialized"
        ):
            CleanupWorker(mock_config)

    @patch("gcp_symphony_operator.workers.cleanup.call_list_namespaced_custom_object")
    async def test_cleanup_resources_no_resources(
        self: Self,
        mock_list_custom_object: AsyncMock,
        mock_config: Config,
    ) -> None:
        """Test cleanup when no resources are found."""
        mock_config._Config__initialized = True
        mock_config.default_namespaces = ["test-namespace"]
        mock_config.crd_plural = "test-plural"
        mock_list_custom_object.return_value = {"items": []}

        worker = CleanupWorker(mock_config)
        await worker._cleanup_resources("test-plural")

        mock_list_custom_object.assert_called_once()
        mock_config.logger.error.assert_not_called()

    async def test_process_gcpsr_no_name(self: Self, mock_config: Config) -> None:
        """Test processing GCPSR with no name."""
        mock_config._Config__initialized = True
        worker = CleanupWorker(mock_config)

        resource = {"metadata": {}}
        await worker._process_gcpsr(resource)

        # Should return early without processing

    async def test_process_gcpsr_not_completed(self: Self, mock_config: Config) -> None:
        """Test processing GCPSR that is not completed."""
        mock_config._Config__initialized = True
        worker = CleanupWorker(mock_config)

        resource = {"metadata": {"name": "test-resource"}, "status": {"conditions": []}}
        await worker._process_gcpsr(resource)

        # Should not delete since no Completed condition

    async def test_process_gcpsr_no_transition_time(
        self: Self, mock_config: Config
    ) -> None:
        """Test processing GCPSR with no lastTransitionTime."""
        mock_config._Config__initialized = True
        worker = CleanupWorker(mock_config)

        resource = {
            "metadata": {"name": "test-resource"},
            "status": {"conditions": [{"type": "Completed", "status": "True"}]},
        }
        await worker._process_gcpsr(resource)

        # Should not delete since no lastTransitionTime

    async def test_process_gcpsr_recent_completion(
        self: Self, mock_config: Config
    ) -> None:
        """Test processing GCPSR with recent completion time."""
        mock_config._Config__initialized = True
        mock_config.crd_completed_retain_time = 60  # 60 minutes
        worker = CleanupWorker(mock_config)

        deleted_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        resource = {
            "metadata": {"name": "test-resource", "namespace": "test-namespace"},
            "status": {
                "conditions": [
                    {
                        "type": "Completed",
                        "status": "True",
                        "lastTransitionTime": deleted_time.isoformat(),
                    }
                ]
            },
        }
        await worker._process_gcpsr(resource)

        # Should not delete since not expired

    @patch("gcp_symphony_operator.workers.cleanup.call_delete_namespaced_custom_object")
    async def test_process_gcpsr_expired_completion(
        self: Self,
        mock_delete_custom_object: AsyncMock,
        mock_config: Config,
    ) -> None:
        """Test processing GCPSR with expired completion time."""
        mock_config._Config__initialized = True
        mock_config.crd_completed_retain_time = 60  # 60 minutes
        mock_config.crd_plural_map = {"TestKind": "test-plural"}
        worker = CleanupWorker(mock_config)

        deleted_time = datetime.now(timezone.utc) - timedelta(minutes=90)
        resource = {
            "kind": "TestKind",
            "metadata": {"name": "test-resource", "namespace": "test-namespace"},
            "status": {
                "conditions": [
                    {
                        "type": "Completed",
                        "status": "True",
                        "lastTransitionTime": deleted_time.isoformat(),
                    }
                ]
            },
        }
        await worker._process_gcpsr(resource)

        # Should delete since expired
        mock_delete_custom_object.assert_called_once_with(
            name="test-resource",
            namespace="test-namespace",
            plural="test-plural",
        )

    @patch("gcp_symphony_operator.workers.cleanup.call_delete_namespaced_custom_object")
    async def test_delete_resource_api_exception(
        self: Self,
        mock_delete_custom_object: AsyncMock,
        mock_config: Config,
    ) -> None:
        """Test delete resource with API exception."""
        mock_config._Config__initialized = True
        mock_config.crd_plural_map = {"TestKind": "test-plural"}
        worker = CleanupWorker(mock_config)

        mock_delete_custom_object.side_effect = ApiException(
            status=500, reason="Test Error"
        )

        resource = {
            "kind": "TestKind",
            "metadata": {"name": "test-resource", "namespace": "test-namespace"},
        }

        await worker._delete_resource(resource)

        mock_delete_custom_object.assert_called_once()
        mock_config.logger.error.assert_called()

    def test_is_expired_true(self: Self, mock_config: Config) -> None:
        """Test _is_expired returns True for old timestamp."""
        mock_config._Config__initialized = True
        mock_config.crd_completed_retain_time = 60  # 60 minutes
        worker = CleanupWorker(mock_config)

        old_time = datetime.now(timezone.utc) - timedelta(minutes=90)
        assert worker._is_expired(old_time.isoformat()) is True

    def test_is_expired_false(self: Self, mock_config: Config) -> None:
        """Test _is_expired returns False for recent timestamp."""
        mock_config._Config__initialized = True
        mock_config.crd_completed_retain_time = 60  # 60 minutes
        worker = CleanupWorker(mock_config)

        recent_time = datetime.now(timezone.utc) - timedelta(minutes=30)
        assert worker._is_expired(recent_time.isoformat()) is False
