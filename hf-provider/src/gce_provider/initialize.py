from __future__ import annotations
import threading
from typing import Any
from gce_provider.db.initialize import main as initialize_db

__all__ = ["ensure_initialized"]

_initialized: bool = False
_init_lock = threading.Lock()

def _init_all(config: Any) -> None:
    """Perform all synchronous initialization logic for the GCE provider."""
    
    # Initialize the database to avoid the need to explicitly declare $HF_DBDIR,
    # thereby simplifying the installation process.
    initialize_db(config)

    # Add other initialization logic here as needed.
    # ...


def ensure_initialized(config: Any) -> None:
    """Synchronous entrypoint that runs initialization exactly once per process."""
    global _initialized

    if _initialized:
        return

    with _init_lock:
        if _initialized:
            return

        config.logger.info("Performing process-level initialization for GCE provider.")

        try:
            _init_all(config)
            _initialized = True
            config.logger.info("Initialization complete.")
        except Exception:
            config.logger.error("Initialization failed.")
            raise
