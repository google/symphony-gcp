from common.utils import path_utils
import pytest
import os
from unittest.mock import patch


def test_normalize_path():
    """Test normalizing path."""
    base_path = "/base/path"
    relative_path = "relative/path"
    expected_path = "/base/path/relative/path"
    assert path_utils.normalize_path(base_path, relative_path) == expected_path


def test_resolve_path_relative_to_function():
    """Test resolving path relative to function."""
    with patch(
        "common.utils.path_utils.os.path.dirname", return_value="/function/path"
    ):
        assert (
            path_utils.resolve_path_relative_to_function("test_path")
            == "/function/path/test_path"
        )
