import sys
import os
from common.utils import path_utils

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)
import pytest
from unittest.mock import MagicMock
from gce_provider.config import get_config
import logging


@pytest.fixture
def mock_config():
    """Fixture to provide a mock Config instance."""
    config = MagicMock(wraps=get_config())
    config.logger = MagicMock()
    return config


@pytest.fixture
def mock_logger():
    """Fixture to provide a mock logger instance."""
    logger = MagicMock(spec=logging.Logger)
    return logger
