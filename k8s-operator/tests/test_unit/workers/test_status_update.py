import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from gcp_symphony_operator.config import Config
from gcp_symphony_operator.workers.status_update import (
    StatusUpdateWorker,
    UpdateEvent,
    create_status_update_queue,
    enqueue_status_update,
    get_gcpsymphonyresource_phase,
)


@pytest.fixture
def mock_update_queue() -> AsyncMock:
    """Fixture for a mock async queue object."""
    return AsyncMock(spec=asyncio.Queue)


@pytest.fixture
def mock_stop_event() -> MagicMock:
    """Fixture for a mock async event object."""
    return MagicMock(spec=asyncio.Event)


@pytest.fixture
def worker(
    mock_config: Config, mock_update_queue: AsyncMock, mock_stop_event: MagicMock
) -> StatusUpdateWorker:
    """Fixture for a StatusUpdateWorker object."""
    mock_config._Config__initialized = True  # type: ignore
    return StatusUpdateWorker(mock_config, mock_update_queue, mock_stop_event)


async def test_collect_batch_updates_empty_queue(
    worker: StatusUpdateWorker, mock_update_queue: AsyncMock
) -> None:
    """Test collecting updates when queue is empty."""
    mock_update_queue.get.side_effect = asyncio.TimeoutError

    updates = await worker._collect_batch_updates()

    assert updates == []
    mock_update_queue.get.assert_called_once()


async def test_collect_batch_updates_with_data(
    worker: StatusUpdateWorker, mock_update_queue: AsyncMock, mock_config: Config
) -> None:
    """Test collecting updates with data in queue."""
    mock_config.crd_update_batch_size = 2

    update_data = {
        "cr_name": "test-resource",
        "namespace": "test-namespace",
        "request_id": "test-request-id",
    }

    mock_update_queue.get.return_value = update_data
    mock_update_queue.get_nowait.side_effect = asyncio.QueueEmpty

    updates = await worker._collect_batch_updates()

    assert len(updates) == 1
    assert updates[0].cr_name == "test-resource"


async def test_start_worker(worker: StatusUpdateWorker, mock_config: Config) -> None:
    """Test starting the worker."""
    await worker.start()

    assert worker.worker_task is not None
    assert not worker.worker_task.done()

    # Clean up
    worker.worker_task.cancel()
    try:
        await worker.worker_task
    except asyncio.CancelledError:
        pass


class TestStatusUpdateWorker:
    """Tests for the StatusUpdateWorker class."""

    @patch("gcp_symphony_operator.workers.status_update.call_get_custom_object")
    @patch(
        "gcp_symphony_operator.workers.status_update.call_patch_namespaced_custom_object_status"
    )
    @patch("gcp_symphony_operator.workers.status_update.get_gcpsymphonyresource_phase")
    async def test_process_consolidated_updates_success(
        self,
        mock_get_phase: AsyncMock,
        mock_patch_status: AsyncMock,
        mock_get_custom_object: AsyncMock,
        worker: StatusUpdateWorker,
        mock_config: Config,
    ) -> None:
        """Test successful processing of consolidated updates."""
        # Setup
        mock_config.crd_kind = "TestKind"
        mock_config.crd_plural = "test-plural"

        mock_get_custom_object.return_value = {
            "metadata": {
                "resourceVersion": "123",
                "labels": {"symphony.requestId": "test-id"},
            },
            "status": {"conditions": [], "returnedMachines": []},
        }
        mock_get_phase.return_value = ("Running", 1)

        update = UpdateEvent(
            cr_name="test-resource",
            namespace="test-namespace",
            request_id="test-request-id",
        )

        # Call the method
        await worker._process_consolidated_updates(
            "test-namespace", "test-resource", [update]
        )

        # Assertions
        mock_get_custom_object.assert_called_once()
        mock_patch_status.assert_called_once()
        mock_config.logger.info.assert_called()  # type: ignore

    @patch("gcp_symphony_operator.workers.status_update.call_get_custom_object")
    async def test_process_consolidated_updates_no_resource_version(
        self,
        mock_get_custom_object: AsyncMock,
        worker: StatusUpdateWorker,
        mock_config: Config,
    ) -> None:
        """Test processing updates when resource has no version."""
        mock_config.crd_kind = "TestKind"
        mock_config.crd_plural = "test-plural"

        mock_get_custom_object.return_value = {
            "metadata": {},  # No resourceVersion
            "status": {},
        }

        update = UpdateEvent(
            cr_name="test-resource",
            namespace="test-namespace",
            request_id="test-request-id",
        )

        # Call the method
        await worker._process_consolidated_updates(
            "test-namespace", "test-resource", [update]
        )

        mock_get_custom_object.assert_called_once()
        mock_config.logger.error.assert_called()  # type: ignore

    async def test_create_status_update_queue(self, mock_config: Config) -> None:
        """Test creating status update queue."""
        queue, stop_event = create_status_update_queue(mock_config)

        assert isinstance(queue, asyncio.Queue)
        assert isinstance(stop_event, asyncio.Event)
        assert not stop_event.is_set()

    @patch("gcp_symphony_operator.workers.status_update.get_op_context")
    async def test_enqueue_status_update(self, mock_get_context: MagicMock) -> None:
        """Test enqueuing a status update."""
        mock_queue = AsyncMock()
        mock_context = MagicMock()
        mock_context.get_update_queue = AsyncMock(return_value=mock_queue)
        mock_get_context.return_value = mock_context

        update = UpdateEvent(
            cr_name="test-resource",
            namespace="test-namespace",
            request_id="test-request-id",
        )

        await enqueue_status_update(update)

        mock_queue.put.assert_called_once()

    @patch("gcp_symphony_operator.workers.status_update.call_list_namespaced_pod")
    async def test_get_gcpsymphonyresource_phase(
        self, mock_list_pods: AsyncMock, mock_config: Config
    ) -> None:
        """Test getting GCPSymphonyResource phase."""
        mock_config.min_request_id_length = 8
        mock_list_pods.return_value.items = []

        phase, count = await get_gcpsymphonyresource_phase(
            request_id="test-request-id",
            namespace="test-namespace",
            logger=mock_config.logger,
            config=mock_config,
        )

        assert phase == "WaitingCleanup"
        assert count == 0
        mock_list_pods.assert_called_once()
