import logging
import os
import sys
from typing import Any, Optional

import kopf

from .config import Config, get_config
from .operator_context import OperatorContext
from .workers.cleanup import CleanupWorker
from .workers.context import (
    get_cleanup_worker,
    get_op_context,
    set_cleanup_worker,
    set_op_context,
)
from .workers.health_server import HealthServer

# Create a context
_health_server: Optional[HealthServer] = None

log_level_str = os.getenv(
    f"{Config.ENV_VAR_PREFIX}KOPF_LOG_LEVEL", Config.DEFAULT_LOG_LEVEL
).upper()
kopf_logger = logging.getLogger("kopf")
kopf_logger.setLevel(
    logging.getLevelName(log_level_str) if log_level_str else logging.INFO
)


def run_operator(config: Config, logger: logging.Logger) -> None:
    """Run the kopf operator with the provided configuration."""
    logger.info(f"Starting GCP Symphony Operator v{config.operator_version}")

    context = OperatorContext(config)
    context.initialize_queue()

    set_op_context(context)

    if not context.update_queue or not context.stop_event:
        raise RuntimeError("Queue not initialized. Call initialize_queue() first.")

    # Set up kopf arguments
    kopf_args = [
        "--verbose",
        "--log-format=json",
        "--server-timeout",
        str(config.kopf_server_timeout),
        "--max-workers",
        str(config.kopf_max_workers),
    ]

    # Run the operator
    sys.argv[1:] = kopf_args
    logger.info(f"Running kopf with arguments: {kopf_args}")
    kopf.run(namespaces=config.default_namespaces, standalone=True)  # type: ignore


@kopf.on.startup()  # type: ignore
async def kopf_startup(settings: kopf.OperatorSettings, **_: Any) -> None:
    """Configure the operator settings on startup."""
    # Using global context variable to ensure it is shared across the module
    global _health_server
    config = await get_config()
    context = get_op_context()
    if context is None:
        config.logger.info("Creating new operator context for kopf.starup")
        context = OperatorContext(config)
        context.initialize_queue()
        set_op_context(context)

    if context is not None:
        try:
            config.logger.info("✅ Starting the status update worker.")
            await context.start_update_worker()
        except Exception as e:
            raise RuntimeError(
                "Failed to start status update worker. Ensure the operator is configured correctly."
            ) from e
    else:
        raise RuntimeError(
            "Operator context is not initialized. Cannot start update worker."
        )

    # Start cleanup worker
    cleanup_worker = get_cleanup_worker()
    if cleanup_worker is None:
        cleanup_worker = CleanupWorker(config)
        set_cleanup_worker(cleanup_worker)
    try:
        config.logger.info("✅ Starting the cleanup worker.")
        await cleanup_worker.start()
    except Exception as e:
        raise RuntimeError(
            "Failed to start cleanup worker. Ensure the operator is configured correctly."
        ) from e

    # Start health server if enabled
    if config.health_check_enabled and _health_server is None:
        try:
            _health_server = HealthServer(config=config)
            _health_server.start()
            config.logger.info(
                f"Health check server started on port {_health_server.port}"
            )
        except Exception as e:
            config.logger.error(
                f"Failed to start health check server: {e}", exc_info=True
            )
    # Mark operator as ready
    context.set_ready(True)
    config.logger.info("Configuring operator settings.")
    try:
        log_level_str = os.getenv(
            f"{Config.ENV_VAR_PREFIX}KOPF_LOG_LEVEL", config.DEFAULT_LOG_LEVEL
        ).upper()
        settings.posting.level = (
            logging.getLevelName(log_level_str) if log_level_str else logging.INFO
        )
        settings.posting.enabled = config.kopf_posting_enabled
        settings.persistence.finalizer = config.crd_finalizer
        settings.persistence.progress_storage = kopf.AnnotationsProgressStorage()
        settings.persistence.diffbase_storage = kopf.AnnotationsDiffBaseStorage()
        # Throttle for unexpected errors in network or api
        settings.batching.error_delays = [10, 20, 30]
        # limit the number of workers to avoid overwhelming the API server
        settings.batching.worker_limit = config.kopf_max_workers
        settings.watching.server_timeout = (
            config.kopf_server_timeout  # 5 make sure the operator doesn't sleep
        )
    except Exception as e:
        raise RuntimeError("Failed to configure kopf settings.") from e


@kopf.on.cleanup()  # type: ignore
async def kopf_cleanup(**_: Any) -> None:
    """Cleanup resources on operator shutdown."""
    global _health_server  # noqa: F824
    config = await get_config()
    try:
        # Stop the operator context first
        if context := get_op_context():
            context.set_ready(False)

            config.logger.info("🛑 Stopping status update worker.")
            await context.stop_update_worker()

        # Stop the cleanup worker if it exists
        if cleanup_worker := get_cleanup_worker():
            config.logger.info("🛑 Stopping cleanup worker.")
            await cleanup_worker.stop()  # type: ignore

        # Stop the health server if it exists
        if _health_server:
            config.logger.info("🛑 Stopping health server.")
            _health_server.stop()

        config.logger.info("✅ Cleanup completed.")
    except Exception as e:
        config.logger.error(f"❌ Error during cleanup: {e}", exc_info=True)
