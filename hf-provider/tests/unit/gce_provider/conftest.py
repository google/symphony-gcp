import pytest
from common.utils import path_utils

@pytest.fixture(autouse=True)
def mock_environment(monkeypatch):
    monkeypatch.setenv(
        "HF_DBDIR", path_utils.resolve_path_relative_to_function("../../scratch")
    )
    monkeypatch.setenv(
        "HF_PROVIDER_CONFDIR",
        path_utils.resolve_path_relative_to_function(
            "../../resources/provider-config/config-001/conf/providers/gcpgceinst"
        ),
    )
