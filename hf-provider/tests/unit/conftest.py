import os
from pathlib import Path

import pytest

_HF_PROVIDER_ROOT = Path(__file__).parents[2]
_CONTRACT_HOST = "contract-host"



@pytest.fixture
def src_dir() -> Path:
    return _HF_PROVIDER_ROOT / "src"


@pytest.fixture
def provider_config_dir() -> Path:
    return (
        _HF_PROVIDER_ROOT
        / "tests"
        / "resources"
        / "provider-config"
        / "config-001"
        / "conf"
        / "providers"
    )


@pytest.fixture
def provider_log_name() -> str:
    return f"gcp-symphony-provider.{_CONTRACT_HOST}.log"


@pytest.fixture
def make_cli_env(src_dir):

    def _make(confdir, log_dir):
        env = os.environ.copy()

        env.pop("HF_PROVIDER_NAME", None)
        env.pop("GCP_HF_LOG_LEVEL", None)
        env["HF_PROVIDER_CONFDIR"] = str(confdir)
        env["HF_PROVIDER_LOGDIR"] = str(log_dir)
        env["EGOSC_INSTANCE_HOST"] = _CONTRACT_HOST
        env["PYTHONPATH"] = str(src_dir) + os.pathsep + env.get("PYTHONPATH", "")
        env["PYTHONWARNINGS"] = "always"

        return env
    
    return _make
