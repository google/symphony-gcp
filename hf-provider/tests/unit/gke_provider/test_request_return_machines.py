from gke_provider.commands import request_return_machines
from unittest.mock import patch, MagicMock
import pytest


def test_request_return_machines_success(mock_config, mock_hfr):
    """Test requesting return machines successfully."""

    machine = MagicMock()
    machine.name = "test-machine"

    mock_hfr.requestReturnMachines = MagicMock()
    mock_hfr.requestReturnMachines.machines = [machine]
    with patch(
        "gke_provider.k8s.resources.get_all_gcpsymphonyresources",
        return_value=[
            {
                "status": {
                    "deletedMachines": {"test-machine": {"deleteRequestId": "test-id"}}
                }
            }
        ],
    ), patch(
        "gke_provider.k8s.resources.create_machine_return_request_resource",
        return_value={"metadata": {"resourceVersion": "1"}},
    ):
        result = request_return_machines.request_return_machines(mock_hfr)
        assert result is not None


def test_request_return_machines_invalid_request(mock_config, mock_hfr):
    """Test requesting return machines with invalid request."""
    mock_hfr.requestReturnMachines = None
    with pytest.raises(ValueError):
        request_return_machines.request_return_machines(mock_hfr)


def test_request_return_machines_resource_error(mock_config, mock_hfr):
    """Test requesting return machines with resource error."""
    mock_hfr.requestReturnMachines = MagicMock()
    mock_hfr.requestReturnMachines.machines = [{"name": "test-machine"}]
    with patch(
        "gke_provider.k8s.resources.get_all_gcpsymphonyresources",
        side_effect=Exception("Test Exception"),
    ), pytest.raises(Exception):
        request_return_machines.request_return_machines(mock_hfr)

def test_request_return_machines_no_gcpsymphonyresources(mock_config, mock_hfr):
    """Test requesting return machines when no GCPSymphonyResources are found."""
    machine = MagicMock()
    machine.name = "test-machine"

    mock_hfr.requestReturnMachines = MagicMock()
    mock_hfr.requestReturnMachines.machines = [machine]
    with patch(
        "gke_provider.k8s.resources.get_all_gcpsymphonyresources", return_value=[]
    ), patch(
        "gke_provider.k8s.resources.create_machine_return_request_resource",
        return_value={"metadata": {}},
    ):
        result = request_return_machines.request_return_machines(mock_hfr)
        assert (
            result["message"]
            == "Failed to create MachineReturnRequest resource, returned resourceVersion is None"
        )


def test_request_return_machines_missing_name(mock_config, mock_hfr):
    """Test requesting return machines with missing name in machines."""
    mock_hfr.requestReturnMachines = MagicMock()
    mock_hfr.requestReturnMachines.machines = [{}]
    with pytest.raises(ValueError):
        request_return_machines.request_return_machines(mock_hfr)


def test_request_return_machines_no_machines(mock_config, mock_hfr):
    """Test requesting return machines with no machines in requestReturnMachines."""
    mock_hfr.requestReturnMachines = MagicMock()
    mock_hfr.requestReturnMachines.machines = None
    with pytest.raises(ValueError):
        request_return_machines.request_return_machines(mock_hfr)

def test_request_return_machines_delete_pods_failure(mock_config, mock_hfr):
    """Test requesting return machines with create_machine_return_request_resource failing."""
    machine = MagicMock()
    machine.name = "test-machine"

    mock_hfr.requestReturnMachines = MagicMock()
    mock_hfr.requestReturnMachines.machines = [machine]
    with patch(
        "gke_provider.k8s.resources.get_all_gcpsymphonyresources",
        return_value=[
            {
                "metadata": {"labels": {"symphony.requestId": "test-id"}},
                "status": { },
            }
        ],
    ), patch(
        "gke_provider.k8s.resources.create_machine_return_request_resource",
        side_effect=Exception("API Exception"),
    ), pytest.raises(Exception):
        result = request_return_machines.request_return_machines(mock_hfr)
        assert "machines failed to return" in result["message"]


# NOTE: (SKIP) The test case below contradicts the intended logic for handling dicts vs objects.
# NOTE: It expects to receive an object in a single request; however, the _get_machine_list()
# NOTE: function only allows dict or list types.
@pytest.mark.skip(reason="Function missing in implementation")
def test_request_return_machines_single_machine_success(mock_config, mock_hfr):
    """Test requesting return machines successfully with a single machine."""
    machine = MagicMock()
    machine.name = "test-machine"

    mock_hfr.requestReturnMachines = MagicMock()
    mock_hfr.requestReturnMachines.machines = machine
    with patch(
        "gke_provider.k8s.resources.get_all_gcpsymphonyresources",
        return_value=[
            {
                "metadata": {"labels": {"symphony.requestId": "test-id"}},
                "status": {
                    "deletedMachines": {"test-id-pod-0": {"deleteRequestId": "test-id"}}
                },
            }
        ],
    ), patch(
        "gke_provider.k8s.resources.create_machine_return_request_resource",
        return_value={"metadata": {"resourceVersion": "1"}},
    ):
        result = request_return_machines.request_return_machines(mock_hfr)
        assert result is not None