import errno
import inspect
import logging
import os
from pathlib import Path
from typing import Optional


def ensure_path_exists(directory_path: str, mode: int = 0o777) -> bool:
    """
    Create a directory with path validation and robust error handling.

    Args:
        directory_path (str): Path to the directory to create.
        mode (int): Permissions for the directory (default: 0o777).

    Returns:
        bool: True if the directory exists or was created successfully, False otherwise.
    """
    if not directory_path or not isinstance(directory_path, str):
        logging.error("Invalid directory path: Must be a non-empty string")
        return False

    try:
        os.makedirs(directory_path, mode=mode, exist_ok=True)
        return True
    except OSError as e:
        if e.errno == errno.EACCES:
            logging.error(
                f"Permission denied: Cannot create directory '{directory_path}'"
            )
        elif e.errno == errno.ENOSPC:
            logging.error(
                f"No space left on device: Cannot create directory '{directory_path}'"
            )
        elif e.errno == errno.ENOENT:
            logging.error(
                f"Invalid path or parent directory does not exist: '{directory_path}'"
            )
        else:
            logging.error(
                f"Unexpected error creating directory '{directory_path}': {e}"
            )
        return False


def normalize_path(base_path: str, relative_path: str) -> str:
    """
    If the relative_path is absolute, return the relative path.
    Otherwise return a normalized path consisting of the relative_path,
    relative to base_path
    :param base_path:
    :param relative_path:
    :return: the normalized path
    """
    path_obj = Path(relative_path)
    if path_obj.is_absolute():
        return relative_path
    else:
        return os.path.normpath(os.path.join(base_path, relative_path))


def resolve_path_relative_to_function(relative_path: str) -> Optional[str]:
    """Resolves a path relative to the directory of the calling function.

    Args:
        relative_path: The path to resolve, relative to the calling function's directory.

    Returns:
        The absolute path.
    """
    # Get the caller's frame
    import inspect

    current_frame = inspect.currentframe()
    if current_frame is None:
        return None
    caller_frame = current_frame.f_back

    # Get the caller's file path
    if caller_frame is None:
        return None
    caller_file_path = caller_frame.f_code.co_filename

    # Get the caller's directory
    caller_dir = os.path.dirname(caller_file_path)

    # Resolve the path
    absolute_path = os.path.abspath(os.path.join(caller_dir, relative_path))

    return absolute_path


def resolve_caller_dir(logger: Optional[logging.Logger] = None) -> Optional[str]:
    """
    Infer the caller's directory.

    Returns:
        The caller's directory as a string, or None if it cannot be determined.
    """
    try:
        stack = inspect.stack()
        if len(stack) < 2:
            if logger:
                logger.warning(
                    "resolve_caller_dir: Not enough frames in the call stack."
                )
            return None

        caller_frame = stack[1]
        caller_module = inspect.getmodule(caller_frame[0])

        if caller_module is None:
            if logger:
                logger.warning(
                    "resolve_caller_dir: Could not determine caller's module."
                )
            return None

        if not hasattr(caller_module, "__file__") or caller_module.__file__ is None:
            if logger:
                logger.warning(
                    "resolve_caller_dir: Caller module "
                    f"{(caller_module.__name__ if hasattr(caller_module, '__name__') else caller_module)}"  # noqa: E501
                    "has no __file__ attribute."
                )
            return None

        caller_dir = os.path.dirname(caller_module.__file__)
        return caller_dir

    except Exception as e:
        if logger:
            logger.exception(
                f"resolve_caller_dir: Error resolving caller directory: {e}"
            )
        return None
