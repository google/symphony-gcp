import time
from functools import wraps
from logging import Logger
from typing import Any, Callable


def log_execution_time(logger: Logger) -> Callable[..., Any]:
    """
    Decorator to log the execution time of a function.
    It also logs any exceptions that occur during the function execution.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                # Log the exception
                logger.exception(f"Exception in {func.__name__}: {e}")
                # Re-raise the exception to propagate it
                raise
            finally:
                end_time = time.time()
                execution_time = end_time - start_time
                logger.debug(f"Function {func.__name__} executed in {execution_time:.4f} seconds")

        return wrapper

    return decorator
