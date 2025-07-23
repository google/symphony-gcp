import os
import sys

from common.utils import path_utils

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)
import pytest
from unittest.mock import MagicMock
from gke_provider.config import Config
import logging


@pytest.fixture(autouse=True)
def mock_environment(monkeypatch):
    monkeypatch.setenv(
        "HF_PROVIDER_CONFDIR",
        path_utils.resolve_path_relative_to_function(
            "../../resources/provider-config/config-001/conf/providers/gcpgkeinst"
        ),
    )


@pytest.fixture
def mock_config():
    """Fixture to provide a mock Config instance."""
    config = MagicMock(spec=Config)
    config.kube_config = "/path/to/kubeconfig"
    config.crd_namespace = "test-namespace"
    config.crd_group = "test-group"
    config.crd_version = "test-version"
    config.crd_plural = "test-plural"
    config.crd_kind = "TestKind"
    config.logger = MagicMock()
    return config


@pytest.fixture
def mock_logger():
    """Fixture to provide a mock logger instance."""
    logger = MagicMock(spec=logging.Logger)
    return logger


@pytest.fixture
def mock_hfr():
    """Fixture to provide a mock HFRequest instance."""
    hfr = MagicMock()
    return hfr


@pytest.fixture
def mock_request_machine_status():
    """Fixture to provide a mock request machine status."""
    return {
        "requestId": "test-request-id",
        "status": "running",
        "details": {
            "podName": "test-pod",
            "deploymentName": "test-deployment",
            "namespace": "test-namespace",
        },
    }
