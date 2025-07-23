import asyncio
import logging
import time
from unittest.mock import Mock

import pytest
from gcp_symphony_operator.profiling import (
    log_execution_time,
    log_execution_time_with_lazy_logger,
)


class TestLogExecutionTime:
    """Test cases for log_execution_time decorator."""

    def test_sync_function_success(self, caplog):
        """Test decorator with successful sync function."""
        logger = logging.getLogger("test")

        @log_execution_time(logger)
        def sync_func(x, y):
            time.sleep(0.01)
            return x + y

        with caplog.at_level(logging.DEBUG):
            result = sync_func(1, 2)

        assert result == 3
        assert "sync_func executed in" in caplog.text
        assert "seconds" in caplog.text

    def test_sync_function_with_exception(self, caplog):
        """Test decorator with sync function that raises exception."""
        logger = logging.getLogger("test")

        @log_execution_time(logger)
        def failing_sync_func():
            raise ValueError("test error")

        with caplog.at_level(logging.DEBUG):
            with pytest.raises(ValueError, match="test error"):
                failing_sync_func()

        assert "Exception in failing_sync_func: test error" in caplog.text
        assert "failing_sync_func executed in" in caplog.text

    @pytest.mark.asyncio
    async def test_async_function_success(self, caplog):
        """Test decorator with successful async function."""
        logger = logging.getLogger("test")

        @log_execution_time(logger)
        async def async_func(x, y):
            await asyncio.sleep(0.01)
            return x * y

        with caplog.at_level(logging.DEBUG):
            result = await async_func(3, 4)

        assert result == 12
        assert "async_func executed in" in caplog.text
        assert "seconds" in caplog.text

    @pytest.mark.asyncio
    async def test_async_function_with_exception(self, caplog):
        """Test decorator with async function that raises exception."""
        logger = logging.getLogger("test")

        @log_execution_time(logger)
        async def failing_async_func():
            await asyncio.sleep(0.001)
            raise RuntimeError("async error")

        with caplog.at_level(logging.DEBUG):
            with pytest.raises(RuntimeError, match="async error"):
                await failing_async_func()

        assert "Exception in failing_async_func: async error" in caplog.text
        assert "failing_async_func executed in" in caplog.text

    def test_preserves_function_metadata(self):
        """Test that decorator preserves original function metadata."""
        logger = logging.getLogger("test")

        @log_execution_time(logger)
        def documented_func():
            """This is a test function."""
            return "test"

        assert documented_func.__name__ == "documented_func"
        assert documented_func.__doc__ == "This is a test function."

    def test_timing_accuracy(self, caplog):
        """Test that timing measurements are reasonably accurate."""
        logger = logging.getLogger("test")

        @log_execution_time(logger)
        def timed_func():
            time.sleep(0.1)
            return "done"

        start = time.time()
        with caplog.at_level(logging.DEBUG):
            timed_func()
        actual_duration = time.time() - start

        # Extract logged duration from caplog
        log_message = [
            record.message
            for record in caplog.records
            if "executed in" in record.message
        ][0]
        logged_duration = float(
            log_message.split("executed in ")[1].split(" seconds")[0]
        )

        # Allow some tolerance for timing variations
        assert abs(logged_duration - actual_duration) < 0.01


class TestLogExecutionTimeWithLazyLogger:
    """Test cases for log_execution_time_with_lazy_logger decorator."""

    @pytest.mark.asyncio
    async def test_lazy_logger_called_at_runtime(self, caplog):
        """Test that logger function is called at runtime, not decoration time."""
        mock_logger = Mock()
        mock_logger.debug = Mock()

        def get_logger():
            return mock_logger

        @log_execution_time_with_lazy_logger(get_logger)
        async def async_func():
            await asyncio.sleep(0.01)
            return "result"

        result = await async_func()

        assert result == "result"
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args[0][0]
        assert "async_func took" in call_args
        assert "seconds" in call_args

    @pytest.mark.asyncio
    async def test_lazy_logger_timing_precision(self):
        """Test timing precision with lazy logger."""
        logged_times = []

        def mock_logger():
            logger = Mock()
            logger.debug = lambda msg: logged_times.append(msg)
            return logger

        @log_execution_time_with_lazy_logger(mock_logger)
        async def timed_func():
            await asyncio.sleep(0.05)
            return "done"

        start = time.time()
        await timed_func()
        actual_duration = time.time() - start

        assert len(logged_times) == 1
        log_message = logged_times[0]
        logged_duration = float(log_message.split("took ")[1].split(" seconds")[0])

        # Verify timing accuracy within reasonable tolerance
        assert abs(logged_duration - actual_duration) < 0.01

    @pytest.mark.asyncio
    async def test_preserves_function_metadata_lazy(self):
        """Test that lazy logger decorator preserves function metadata."""

        def get_logger():
            return Mock()

        @log_execution_time_with_lazy_logger(get_logger)
        async def documented_async_func():
            """Async function with documentation."""
            return "test"

        assert documented_async_func.__name__ == "documented_async_func"
        assert documented_async_func.__doc__ == "Async function with documentation."

    @pytest.mark.asyncio
    async def test_logger_function_called_each_time(self):
        """Test that logger function is called on each function execution."""
        call_count = 0

        def get_logger():
            nonlocal call_count
            call_count += 1
            logger = Mock()
            logger.debug = Mock()
            return logger

        @log_execution_time_with_lazy_logger(get_logger)
        async def test_func():
            return "result"

        await test_func()
        await test_func()

        assert call_count == 2


class TestIntegration:
    """Integration tests for profiling decorators."""

    def test_both_decorators_with_real_logger(self, caplog):
        """Test both decorators work with real logger instance."""
        logger = logging.getLogger("integration_test")

        @log_execution_time(logger)
        def sync_func():
            return "sync_result"

        def get_logger():
            return logger

        @log_execution_time_with_lazy_logger(get_logger)
        async def async_func():
            return "async_result"

        with caplog.at_level(logging.DEBUG):
            sync_result = sync_func()

        assert sync_result == "sync_result"
        assert "sync_func executed in" in caplog.text

    @pytest.mark.asyncio
    async def test_nested_decorated_functions(self, caplog):
        """Test behavior when decorated functions call each other."""
        logger = logging.getLogger("nested_test")

        @log_execution_time(logger)
        def inner_func(x):
            return x * 2

        @log_execution_time(logger)
        def outer_func(x):
            return inner_func(x) + 1

        with caplog.at_level(logging.DEBUG):
            result = outer_func(5)

        assert result == 11
        assert "inner_func executed in" in caplog.text
        assert "outer_func executed in" in caplog.text
