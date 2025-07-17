"""
Unit tests for the config.py module.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)
from gcp_symphony_operator.config import Config, get_config, load_config  # noqa: E402

pytestmark = pytest.mark.asyncio


class TestConfig:
    """Tests for the Config class."""

    @pytest.mark.asyncio
    async def test_singleton_pattern(self) -> None:
        """Test that Config follows the singleton pattern."""
        config1 = await Config.create()
        config2 = await Config.create()
        assert config1 == config2

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GCP_HF_LOG_LEVEL": "DEBUG"})
    async def test_environment_variable_override(self) -> None:
        """Test that environment variables override default values."""
        # Reset the singleton instance to force reinitialization
        Config._instance = None

        config = await Config.create()
        assert config.log_level == "DEBUG"

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GCP_HF_DEFAULT_NAMESPACES": "test-namespace"})
    async def test_get_default_namespaces_string(self) -> None:
        """Test _get_default_namespaces with string input."""
        # Reset the singleton instance to force reinitialization
        Config._instance = None

        config = await Config.create()
        assert config.default_namespaces == ["test-namespace"]

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GCP_HF_CRD_COMPLETED_CHECK_INTERVAL": "invalid"})
    async def test_get_crd_completed_check_interval_invalid(self) -> None:
        """Test _get_crd_completed_check_interval with invalid input."""
        # Reset the singleton instance to force reinitialization
        Config._instance = None

        config = await Config.create()
        assert (
            config._get_crd_completed_check_interval()
            == Config.DEFAULT_CRD_COMPLETED_CHECK_INTERVAL
        )

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GCP_HF_CRD_COMPLETED_CHECK_INTERVAL": "-5"})
    async def test_get_crd_completed_check_interval_negative(self) -> None:
        """Test _get_crd_completed_check_interval with negative input."""
        # Reset the singleton instance to force reinitialization
        Config._instance = None

        config = await Config.create()
        assert (
            config._get_crd_completed_check_interval()
            == Config.DEFAULT_CRD_COMPLETED_CHECK_INTERVAL
        )

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GCP_HF_CRD_COMPLETED_CHECK_INTERVAL": "30"})
    async def test_get_crd_completed_check_interval_valid(self) -> None:
        """Test _get_crd_completed_check_interval with valid input."""
        # Reset the singleton instance to force reinitialization
        Config._instance = None

        config = await Config.create()
        assert config._get_crd_completed_check_interval() == 30

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GCP_HF_KUBERNETES_RBAC_CHECK": "true"})
    async def test_boolean_environment_variable(self) -> None:
        """Test boolean environment variable parsing."""
        # Reset the singleton instance to force reinitialization
        Config._instance = None

        config = await Config.create()
        assert config.kubernetes_rbac_check is True

    @pytest.mark.asyncio
    @patch.dict(os.environ, {"GCP_HF_KUBERNETES_RBAC_CHECK": "false"})
    async def test_boolean_environment_variable_false(self) -> None:
        """Test boolean environment variable parsing with false value."""
        # Reset the singleton instance to force reinitialization
        Config._instance = None

        config = await Config.create()
        assert config.kubernetes_rbac_check is False


@pytest.mark.asyncio
async def test_get_config() -> None:
    """Test the get_config function."""
    config1 = await get_config()
    config2 = await get_config()
    assert config1 == config2
    assert isinstance(config1, Config)


@pytest.mark.asyncio
@patch("gcp_symphony_operator.config.Config.create")
async def test_load_config(mock_config_create: MagicMock) -> None:
    """Test the load_config function."""
    mock_config_instance = MagicMock()
    mock_config_create.return_value = mock_config_instance

    await load_config()

    mock_config_create.assert_called_once()
