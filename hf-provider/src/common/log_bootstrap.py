import logging
import logging.handlers
import os
import socket
import tempfile
from typing import Iterator, Optional


ENV_HF_PROVIDER_NAME = "HF_PROVIDER_NAME"
ENV_HF_PROVIDER_LOGDIR = "HF_PROVIDER_LOGDIR"
ENV_EGOSC_INSTANCE_HOST = "EGOSC_INSTANCE_HOST"
ENV_BOOTSTRAP_LOG_LEVEL = "GCP_HF_LOG_LEVEL"

DEFAULT_HF_PROVIDER_NAME = "gcp-symphony"
DEFAULT_LOG_LEVEL = "WARNING"
DEFAULT_LOG_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
DEFAULT_LOG_BACKUP_COUNT = 5

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"

# https://docs.python.org/3.9/library/logging.html#logging-levels
_LEVEL_NAMES = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
    "NOTSET": logging.NOTSET,
}


class _ProviderLogHandler(logging.handlers.RotatingFileHandler):
    """Marker type for the handler this module manages on the root logger."""


class _ProviderNullHandler(logging.NullHandler):
    """Marker for the degraded mode where no log location is writable."""


def _installed_handler() -> Optional[logging.Handler]:
    """Return the handler installed on the root logger, if any."""
    return next(
        (
            handler
            for handler in logging.getLogger().handlers
            if isinstance(handler, (_ProviderLogHandler, _ProviderNullHandler))
        ),
        None,
    )


def _hostname() -> str:
    try:
        return socket.gethostname()
    except Exception:
        return "localhost"


def _log_filename() -> str:
    hf_provider_name = os.environ.get(ENV_HF_PROVIDER_NAME) or DEFAULT_HF_PROVIDER_NAME
    hostname = os.environ.get(ENV_EGOSC_INSTANCE_HOST) or _hostname()
    return f"{hf_provider_name}-provider.{hostname}.log"


def _candidate_log_files() -> Iterator[str]:
    filename = _log_filename()
    log_dir = os.environ.get(ENV_HF_PROVIDER_LOGDIR)
    if log_dir:
        yield os.path.join(log_dir, filename)
    yield os.path.join(tempfile.gettempdir(), filename)


def default_log_file() -> str:
    return next(_candidate_log_files())


def _resolve_level(level: Optional[str]) -> int:
    return _LEVEL_NAMES.get((level or DEFAULT_LOG_LEVEL).upper(), logging.WARNING)


def _create_file_handler(
        logfile: str, max_bytes: int, backup_count: int
)-> Optional["_ProviderLogHandler"]:
    try:
        handler = _ProviderLogHandler(
            filename=logfile, maxBytes=max_bytes, backupCount=backup_count
        )
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        return handler
    except (OSError, ValueError):
        return None


def _install_handler(handler: logging.Handler) -> None:
    root_logger = logging.getLogger()
    for existing_handler in list(root_logger.handlers):
        if isinstance(existing_handler, (_ProviderLogHandler, _ProviderNullHandler)):
            root_logger.removeHandler(existing_handler)
            try:
                existing_handler.close()
            except Exception:
                pass
    root_logger.addHandler(handler)


def bootstrap_logging() -> None:
    """ Initialize logging for the provider. 
    Must be called first before any third-party import.
    """
    if _installed_handler() is not None:
        return
    
    logging.raiseExceptions = False

    root_logger = logging.getLogger()
    root_logger.setLevel(_resolve_level(os.environ.get(ENV_BOOTSTRAP_LOG_LEVEL)))

    handler : Optional[logging.Handler] = None
    for candidate_logfile in _candidate_log_files():
        handler = _create_file_handler(
            logfile=candidate_logfile,
            max_bytes=DEFAULT_LOG_MAX_BYTES,
            backup_count=DEFAULT_LOG_BACKUP_COUNT,
        )
        if handler is not None:
            break
    if handler is None:
        handler = _ProviderNullHandler()

    _install_handler(handler)
    logging.captureWarnings(True)


def configure_logging(
    logfile: Optional[str] = None,
    level: Optional[str] = None,
    max_bytes: Optional[int] = None,
    backup_count: Optional[int] = None
) -> None:
    """Re-apply log file, level, and rotation settings from the provider JSON configuration.

    Args:
        logfile: Path to the log file.
        level: Logging level.
        max_bytes: Maximum size of each log file.
        backup_count: Number of backup log files to keep.
    """
    if _installed_handler() is None:
        bootstrap_logging()

    if level is not None:
        logging.getLogger().setLevel(_resolve_level(level))
    
    if logfile is None:
        return

    target_max_bytes = DEFAULT_LOG_MAX_BYTES if max_bytes is None else max_bytes
    target_backup_count = DEFAULT_LOG_BACKUP_COUNT if backup_count is None else backup_count

    current_handler = _installed_handler()
    # old one closed first
    if (
        
        isinstance(current_handler, _ProviderLogHandler)
        and os.path.abspath(current_handler.baseFilename) == os.path.abspath(logfile)
        and current_handler.maxBytes == target_max_bytes
        and current_handler.backupCount == target_backup_count
    ):
        return
    
    new_handler = _create_file_handler(
        logfile=logfile,
        max_bytes=target_max_bytes,
        backup_count=target_backup_count,
    )

    if new_handler is None:
        logging.getLogger(__name__).warning(
            "Could not open configured log file %r, keeping the current log target",
            logfile,
        )
        return
    _install_handler(new_handler)
