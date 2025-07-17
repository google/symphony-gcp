"""
Unit tests for the main.py module.
"""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from gcp_symphony_operator.main import main, parse_args
from typing_extensions import Self


class TestParseArgs:
    """Tests for the parse_args function."""

    @patch("sys.argv", ["main.py"])
    def test_parse_args_no_action(self: Self) -> None:
        """Test parsing args with no action."""
        args = parse_args()
        assert args.action is None

    @patch("sys.argv", ["main.py", "export-manifests"])
    def test_parse_args_export_manifests(self: Self) -> None:
        """Test parsing args with export-manifests action."""
        args = parse_args()
        assert args.action == "export-manifests"
        assert args.separate_files is None

    @patch("sys.argv", ["main.py", "export-manifests", "--separate-files", "/path"])
    def test_parse_args_export_manifests_with_path(self: Self) -> None:
        """Test parsing args with export-manifests and separate-files."""
        args = parse_args()
        assert args.action == "export-manifests"
        assert args.separate_files == "/path"


class TestMain:
    """Tests for the main function."""

    @patch("gcp_symphony_operator.main.parse_args")
    @patch("gcp_symphony_operator.main.Manifests")
    def test_main_export_manifests(
        self: Self,
        mock_manifests_class: Any,
        mock_parse_args: Any,
    ) -> None:
        """Test main function with export-manifests action."""
        # Setup
        mock_args = MagicMock()
        mock_args.action = "export-manifests"
        mock_args.separate_files = None
        mock_parse_args.return_value = mock_args

        mock_manifests = MagicMock()
        mock_manifests_class.return_value = mock_manifests

        # Call the function
        main()

        # Assertions
        mock_manifests_class.assert_called_once()
        mock_manifests.export_manifest.assert_called_once_with(
            target_path=None, separate_files=False
        )

    @patch("gcp_symphony_operator.main.parse_args")
    @patch("gcp_symphony_operator.main.Config.create")
    @patch("gcp_symphony_operator.main.check_operator_setup")
    @patch("gcp_symphony_operator.main.register_handlers")
    @patch("gcp_symphony_operator.main.run_operator")
    @patch("asyncio.new_event_loop")
    @patch("asyncio.set_event_loop")
    @patch("logging.getLogger")
    def test_main_run_operator(
        self: Self,
        mock_get_logger: Any,
        mock_set_event_loop: Any,
        mock_new_event_loop: Any,
        mock_run_operator: Any,
        mock_register_handlers: Any,
        mock_check_setup: Any,
        mock_config_create: Any,
        mock_parse_args: Any,
    ) -> None:
        """Test main function running the operator."""
        # Setup
        mock_args = MagicMock()
        mock_args.action = None
        mock_parse_args.return_value = mock_args

        mock_loop = MagicMock()
        mock_new_event_loop.return_value = mock_loop

        mock_config = MagicMock()
        mock_config.kubernetes_client_log_level = "INFO"
        mock_loop.run_until_complete.side_effect = [mock_config, None]

        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Call the function
        main()

        # Assertions
        mock_new_event_loop.assert_called_once()
        mock_set_event_loop.assert_called_once_with(mock_loop)
        assert mock_loop.run_until_complete.call_count == 2
        mock_register_handlers.assert_called_once_with(mock_config)
        mock_run_operator.assert_called_once_with(mock_config, mock_config.logger)

    @patch("gcp_symphony_operator.main.parse_args")
    @patch("gcp_symphony_operator.main.Config.create")
    @patch("gcp_symphony_operator.main.check_operator_setup")
    @patch("asyncio.new_event_loop")
    @patch("asyncio.set_event_loop")
    def test_main_with_exception(
        self: Self,
        mock_set_event_loop: Any,
        mock_new_event_loop: Any,
        mock_check_setup: Any,
        mock_config_create: Any,
        mock_parse_args: Any,
    ) -> None:
        """Test main function with exception."""
        # Setup
        mock_args = MagicMock()
        mock_args.action = None
        mock_parse_args.return_value = mock_args

        mock_loop = MagicMock()
        mock_new_event_loop.return_value = mock_loop

        mock_config = MagicMock()
        mock_config.kubernetes_client_log_level = "INFO"
        mock_loop.run_until_complete.side_effect = [
            mock_config,
            Exception("Test exception"),
        ]

        # Call the function and expect exception
        with pytest.raises(Exception, match="Test exception"):
            main()

        # Assertions
        mock_config.logger.error.assert_called_once()
        mock_config.logger.debug.assert_called_once()
