from gke_provider.commands import request_machines
from unittest.mock import patch, MagicMock
import pytest


def test_request_machines_success(mock_config, mock_hfr):
    """Test requesting machines successfully."""
    mock_hfr.requestMachines = MagicMock()
    mock_hfr.requestMachines.template = MagicMock()
    mock_hfr.requestMachines.template.machineCount = 2
    mock_config.crd_label_name_text = "test-label"
    mock_config.crd_label_value_text = "test-value"
    mock_hfr.pod_spec = {"test": "spec"}
    with patch(
        "gke_provider.k8s.resources.create_gcpsymphonyresource",
        return_value={"metadata": {"name": "test-resource"}},
    ):
        result = request_machines.request_machines(mock_hfr, mock_config)
        assert result is not None


def test_request_machines_invalid_request(mock_config, mock_hfr):
    """Test requesting machines with invalid request."""
    mock_hfr.requestMachines = None
    with pytest.raises(ValueError):
        request_machines.request_machines(mock_hfr, mock_config)


def test_request_machines_resource_error(mock_config, mock_hfr):
    """Test requesting machines with resource error."""
    mock_hfr.requestMachines = MagicMock()
    mock_hfr.requestMachines.template = MagicMock()
    mock_hfr.requestMachines.template.machineCount = 2
    mock_hfr.pod_spec = {"test": "spec"}
    with patch(
        "gke_provider.k8s.resources.create_gcpsymphonyresource",
        side_effect=Exception("Test Exception"),
    ), pytest.raises(Exception):
        request_machines.request_machines(mock_hfr, mock_config)