import pytest
from unittest.mock import patch, MagicMock
import gke_provider.commands.get_return_requests as get_return_requests

def test_get_return_machine_status_success(mock_config, mock_hfr):
    """Test getting return machine status successfully."""
    mock_hfr.returnRequests = MagicMock()
    mock_hfr.returnRequests.machines = [{"name": "test-machine"}]
    with patch(
        "gke_provider.k8s.resources.get_all_gcpsymphonyresources",
        return_value=[
            {
                "status": {
                    "deletedMachines": {"test-machine": {"deleteRequestId": "test-id"}}
                }
            }
        ],
    ):
        
        result = get_return_requests.get_return_requests(mock_hfr, mock_config)
        assert result is not None


def test_get_return_machine_status_no_return_requests(mock_config, mock_hfr):
    """Test getting return machine status with no return requests."""
    mock_hfr.returnRequests = None

    result = get_return_requests.get_return_requests(mock_hfr, mock_config)
    assert "returnRequests must be present" in result["message"]


def test_get_return_machine_status_resource_error(mock_config, mock_hfr):
    """Test getting return machine status with resource error."""
    mock_hfr.returnRequests = MagicMock()
    mock_hfr.returnRequests.machines = [{"name": "test-machine"}]
    with patch(
        "gke_provider.k8s.resources.get_all_gcpsymphonyresources",
        side_effect=Exception("Test Exception"),
    ), pytest.raises(Exception):

        get_return_requests.get_return_requests(mock_hfr, mock_config)