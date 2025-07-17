"""Module to store shared state between components."""

import asyncio
import asyncio.queues as aio_queue
from typing import Optional

# Shared state variables
_op_context = None
_cleanup_worker = None
update_queue: Optional[aio_queue.Queue] = None
stop_event: Optional[asyncio.Event] = None


def get_op_context():
    """Get the operator context."""
    return _op_context


def set_op_context(context):
    """Set the operator context."""
    global _op_context
    _op_context = context


def get_update_queue():
    """Get the update queue."""
    return update_queue


def set_update_queue(queue):
    """Set the update queue."""
    global update_queue
    update_queue = queue


def get_stop_event():
    """Get the stop event."""
    return stop_event


def set_stop_event(event):
    """Set the stop event."""
    global stop_event
    stop_event = event


def set_cleanup_worker(worker):
    """Set the cleanup worker."""
    global _cleanup_worker
    _cleanup_worker = worker


def get_cleanup_worker():
    """Get the cleanup worker."""
    return _cleanup_worker
