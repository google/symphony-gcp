"""Operator context to manage shared state without global variables."""

import asyncio
import asyncio.queues as aio_queue
from typing import Optional

from .config import Config
from .workers.context import set_stop_event, set_update_queue
from .workers.status_update import (
    StatusUpdateWorker,
    create_status_update_queue,
)


class OperatorContext:
    """Encapsulates shared operator state."""

    _initialized = False

    def __init__(self, config: Config):
        if self._initialized:
            return
        self.config = config
        self.update_queue: Optional[aio_queue.Queue] = None
        self.stop_event: Optional[asyncio.Event] = None
        self.update_worker: Optional[StatusUpdateWorker] = None
        self._ready = False
        self._initialized = True

    def initialize_queue(self) -> None:
        """Initialize the status update queue and stop event."""
        if not self.update_queue and not self.stop_event:
            self.config.logger.info(
                "OperatorContext is creating status update queue and stop event"
            )
            self.update_queue, self.stop_event = create_status_update_queue(self.config)
        set_update_queue(self.update_queue)
        set_stop_event(self.stop_event)

    async def start_update_worker(self) -> None:
        """Start the status update worker."""
        if not self.update_queue or not self.stop_event:
            raise RuntimeError("Queue not initialized. Call initialize_queue() first.")

        self.update_worker = StatusUpdateWorker(
            self.config, self.update_queue, self.stop_event  # type: ignore
        )
        await self.update_worker.start()

    async def stop_update_worker(self) -> None:
        """Stop the status update worker."""
        if self.update_worker and self.stop_event:
            self.stop_event.set()  # Signal the worker to stop

            if self.update_worker:
                try:
                    await self.update_worker.stop()
                except Exception as e:
                    self.config.logger.error("Error stopping update worker: %s", e)

    def is_ready(self) -> bool:
        """Check if the operator is ready to handle requests."""
        return (
            self._ready
            and self.update_queue is not None
            and self.update_worker is not None
        )

    async def get_update_queue(self) -> aio_queue.Queue:
        """Ensure update_queue is created and return it."""
        if self.update_queue is None:
            self.initialize_queue()
        return self.update_queue  # type: ignore

    def set_ready(self, ready: bool = True) -> None:
        """Set the operator readiness state."""
        self._ready = ready
