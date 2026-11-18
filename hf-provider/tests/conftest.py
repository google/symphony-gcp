import os
import sys
from pathlib import Path

import pytest

# ensure that modules are properly imported from the "src" directory and "tests" directory
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

_CONTRACT_HOST = "contract-host"


@pytest.fixture
def src_dir() -> Path:
    return ROOT / "src"


@pytest.fixture
def provider_config_dir() -> Path:
    return ROOT / "tests" / "resources" / "provider-config" / "config-001" / "conf" / "providers"


@pytest.fixture
def provider_log_name() -> str:
    return f"gcp-symphony-provider.{_CONTRACT_HOST}.log"


@pytest.fixture
def make_cli_env(src_dir: Path):
    """Build the environment HostFactory sets when it invokes a provider CLI."""

    def _make(confdir: Path, log_dir: Path) -> "dict[str, str]":
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
