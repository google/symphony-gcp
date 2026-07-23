import json
from unittest.mock import MagicMock, patch

import pytest
from google.oauth2 import service_account

from gce_provider.config import Config
from gce_provider.utils import client_factory


@pytest.fixture(autouse=True)
def clear_credentials_cache():
    client_factory.get_credentials.cache_clear()


def make_config(credentials_file, conf_dir):
    config = MagicMock(spec=Config)
    config.gcp_credentials_file = credentials_file
    config.hf_provider_conf_dir = conf_dir
    config.logger = MagicMock()
    return config


def test_returns_none_when_no_credentials_file():
    """With no credentials file set, fall back to application default credentials."""
    config = make_config(credentials_file=None, conf_dir="/some/dir")
    assert client_factory.get_credentials(config) is None


def test_uses_global_config_when_none_passed():
    """When called with no config, load the global config via get_config()."""
    with patch.object(client_factory, "get_config") as mock_get_config:
        mock_get_config.return_value = make_config(
            credentials_file=None, conf_dir="/some/dir"
        )
        result = client_factory.get_credentials(None)

    assert result is None
    mock_get_config.assert_called_once()


def test_raises_when_file_missing(tmp_path):
    """Configured but missing credentials file fails fast instead of falling back to ADC."""
    config = make_config(credentials_file="missing_gcp_credentials_file.json", conf_dir=str(tmp_path))

    with pytest.raises(RuntimeError, match="does not exist"):
        client_factory.get_credentials(config)


def test_resolves_relative_path_against_confdir(tmp_path):
    """Relative credential path resolves against the provider config directory."""
    sa_info = {"type": "service_account", "project_id": "test-project"}
    creds = tmp_path / "test_gcp_credentials_file.json"
    creds.write_text(json.dumps(sa_info))
    config = make_config(credentials_file="test_gcp_credentials_file.json", conf_dir=str(tmp_path))

    sentinel = object()
    with patch.object(
        service_account.Credentials,
        "from_service_account_info",
        return_value=sentinel,
    ) as mock_from_info:
       result = client_factory.get_credentials(config)

    assert result is sentinel
    mock_from_info.assert_called_once_with(sa_info)


def test_raises_when_credential_load_fails(tmp_path):
    """When GCP rejects the key file, fail fast instead of falling back to ADC"""
    creds = tmp_path / "test_gcp_credentials_file.json"
    creds.write_text("{}")
    config = make_config(credentials_file="test_gcp_credentials_file.json", conf_dir=str(tmp_path))

    with pytest.raises(RuntimeError, match="could not be loaded"):
        with patch.object(
            service_account.Credentials,
            "from_service_account_info",
            side_effect=ValueError("bad key"),
        ):
            client_factory.get_credentials(config)