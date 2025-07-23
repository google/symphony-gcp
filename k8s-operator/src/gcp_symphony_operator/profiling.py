import asyncio
import time
from functools import wraps
from logging import Logger
from typing import Any, Callable


def log_execution_time(logger: Logger) -> Callable[..., Any]:
    """
    Decorator to log execution time for both sync and async functions.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    logger.exception(f"Exception in {func.__name__}: {e}")
                    raise
                finally:
                    execution_time = time.time() - start_time
                    logger.debug(
                        f"Function {func.__name__} executed in {execution_time:.4f} seconds"
                    )

            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    logger.exception(f"Exception in {func.__name__}: {e}")
                    raise
                finally:
                    execution_time = time.time() - start_time
                    logger.debug(
                        f"Function {func.__name__} executed in {execution_time:.4f} seconds"
                    )

            return sync_wrapper

    return decorator


def log_execution_time_with_lazy_logger(get_logger_fn):
    """A version of log_execution_time that gets the logger at runtime"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            logger = get_logger_fn()
            start_time = time.time()
            result = await func(*args, **kwargs)
            elapsed_time = time.time() - start_time
            logger.debug(f"{func.__name__} took {elapsed_time:.6f} seconds")
            return result

        return wrapper

    return decorator
