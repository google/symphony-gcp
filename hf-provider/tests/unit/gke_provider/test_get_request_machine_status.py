from gke_provider.commands import get_request_machine_status
from unittest.mock import patch, MagicMock
import pytest
from common.model.models import HFRequestStatus
import datetime


def test_get_request_machine_status_success(mock_config, mock_hfr):
    """Test getting request machine status successfully."""
    mock_hfr.requestStatus = MagicMock(spec=HFRequestStatus)
    mock_hfr.requestStatus.requests = [{"requestId": "test-request-id"}]
    with patch(
        "gke_provider.k8s.resources.get_resource_and_pod_status",
        return_value={"phase": "Running", "pods": []},
    ), patch(
        "gke_provider.commands.get_request_machine_status._process_resource",
        return_value={
            "requestId": "test-request-id",
            "message": "",
            "status": "running",
            "machines": [],
        },
    ):
        result = get_request_machine_status.get_request_machine_status(
            mock_hfr, mock_config
        )
        assert result is not None


def test_get_request_machine_status_success_no_config(mock_config: MagicMock, mock_hfr):
    """Test getting request machine status without providing a config."""
    mock_hfr.requestStatus = MagicMock(spec=HFRequestStatus)
    mock_hfr.requestStatus.requests = [{"requestId": "test-request-id"}]
    with patch(
        "gke_provider.k8s.resources.get_resource_and_pod_status",
        return_value={"phase": "Running", "pods": []},
    ), patch(
        "gke_provider.commands.get_request_machine_status._process_resource",
        return_value={
            "requestId": "test-request-id",
            "message": "",
            "status": "running",
            "machines": [],
        },
    ):
        result = get_request_machine_status.get_request_machine_status(mock_hfr, None)
        assert result is not None


def test_get_request_machine_status_invalid_request(mock_config, mock_hfr):
    """Test getting request machine status with invalid request."""
    mock_hfr.requestStatus = None
    with pytest.raises(ValueError):
        get_request_machine_status.get_request_machine_status(mock_hfr, mock_config)


def test_get_request_machine_status_no_request_ids(mock_config, mock_hfr):
    """Test getting request machine status with invalid request."""
    mock_hfr.requestStatus = MagicMock()
    mock_hfr.requestStatus.requests = [{"request_id": "None"}]
    with patch(
        "gke_provider.k8s.resources.get_resource_and_pod_status",
        return_value={"phase": "Running", "pods": []},
    ), pytest.raises(ValueError):
        get_request_machine_status.get_request_machine_status(mock_hfr, mock_config)


def test_get_request_machine_status_no_requests(mock_config, mock_hfr):
    """Test getting request machine status with no requests."""
    mock_hfr.requestStatus = MagicMock()
    mock_hfr.requestStatus.requests = []
    with pytest.raises(ValueError):
        get_request_machine_status.get_request_machine_status(mock_hfr, mock_config)


def test_get_request_machine_status_resource_error(mock_config, mock_hfr):
    """Test getting request machine status with resource error."""
    mock_hfr.requestStatus = MagicMock()
    mock_hfr.requestStatus.requests = [{"requestId": "test-request-id"}]
    with patch(
        "gke_provider.k8s.resources.get_resource_and_pod_status", return_value="Error"
    ), pytest.raises(ValueError):
        get_request_machine_status.get_request_machine_status(mock_hfr, mock_config)


def test_process_resource_error_phase():
    """Test _process_resource when the phase is in error."""
    resource = {"phase": {"error": "Some error"}, "pods": []}
    request_id = "test-request-id"
    result = get_request_machine_status._process_resource(resource, request_id)
    assert result["status"] == get_request_machine_status.STATUS_COMPLETE_WITH_ERROR
    assert result["message"] == f"Error getting information for requestId: {request_id}"


def test_process_resource_pod_executing():
    """Test _process_resource when a pod is executing."""
    resource = {"phase": "Running", "pods": [{"status": {"phase": "pending"}}]}
    request_id = "test-request-id"
    with patch(
        "gke_provider.commands.get_request_machine_status._extract_pod_details",
        return_value={"status": "running", "result": "executing"},
    ):
        result = get_request_machine_status._process_resource(resource, request_id)
    assert result["status"] == get_request_machine_status.STATUS_RUNNING
    assert result["message"] == "Some machines are still being deployed."


def test_process_resource_pod_failed():
    """Test _process_resource when a pod has failed."""
    resource = {"phase": "Running", "pods": [{"status": {"phase": "failed"}}]}
    request_id = "test-request-id"
    with patch(
        "gke_provider.commands.get_request_machine_status._extract_pod_details",
        return_value={"status": "terminated", "result": "fail"},
    ):
        result = get_request_machine_status._process_resource(resource, request_id)
    assert result["status"] == get_request_machine_status.STATUS_COMPLETE_WITH_ERROR
    assert result["message"] == "Some machines have failed."


def test_process_resource_complete():
    """Test _process_resource when all pods are complete."""
    resource = {"phase": "Running", "pods": [{"status": {"phase": "succeeded"}}]}
    request_id = "test-request-id"
    with patch(
        "gke_provider.commands.get_request_machine_status._extract_pod_details",
        return_value={"status": "stopped", "result": "succeed"},
    ):
        result = get_request_machine_status._process_resource(resource, request_id)
    assert result["status"] == get_request_machine_status.STATUS_COMPLETE
    assert result["message"] is None
    assert result["requestId"] == request_id
    assert "machines" in result


def test_get_request_list_single_request(mock_hfr):
    """Test _get_request_list when a single request is provided."""
    mock_hfr.requestStatus = MagicMock()
    mock_hfr.requestStatus.requests = {"requestId": "test-request-id"}
    single_request, requests = get_request_machine_status._get_request_list(mock_hfr)
    assert single_request is True
    assert requests == [{"requestId": "test-request-id"}]


def test_get_request_list_multiple_requests(mock_hfr):
    """Test _get_request_list when multiple requests are provided."""
    mock_hfr.requestStatus = MagicMock()
    mock_hfr.requestStatus.requests = [
        {"requestId": "test-request-id-1"},
        {"requestId": "test-request-id-2"},
    ]
    single_request, requests = get_request_machine_status._get_request_list(mock_hfr)
    assert single_request is False
    assert requests == [
        {"requestId": "test-request-id-1"},
        {"requestId": "test-request-id-2"},
    ]


def test_get_request_list_invalid_request_format(mock_hfr):
    """Test _get_request_list when an invalid request format is provided."""
    mock_hfr.requestStatus = MagicMock()
    mock_hfr.requestStatus.requests = "invalid"
    with pytest.raises(ValueError) as excinfo:
        get_request_machine_status._get_request_list(mock_hfr)
    assert (
        str(excinfo.value)
        == "Invalid request format: requests should include a single or list of objects"
    )


def test_datetime_to_utc_int_with_timezone():
    """Test datetime_to_utc_int with a datetime object that has a timezone."""
    dt = datetime.datetime(2024, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
    timestamp = get_request_machine_status.datetime_to_utc_int(dt)
    assert timestamp == 1704067200


def test_datetime_to_utc_int_without_timezone():
    """Test datetime_to_utc_int with a datetime object that does not have a timezone."""
    dt = datetime.datetime(2024, 1, 1, 0, 0, 0)
    timestamp = get_request_machine_status.datetime_to_utc_int(dt)
    assert timestamp == 1704088800


def test_extract_pod_details():
    """Test _extract_pod_details function."""
    pod = {
        "metadata": {
            "uid": "test-uid",
            "name": "test-name",
            "namespace": "test-namespace",
        },
        "status": {
            "phase": "running",
            "pod_ip": "10.0.0.1",
            "start_time": datetime.datetime(2024, 1, 1, 0, 0, 0),
        },
    }
    with patch(
        "gke_provider.commands.get_request_machine_status._map_pod_results",
        return_value=("running", "succeed"),
    ):
        result = get_request_machine_status._extract_pod_details(pod)
        assert result["machineId"] == "test-uid"
        assert result["name"] == "test-name"
        assert result["result"] == "succeed"
        assert result["status"] == "running"
        assert result["privateIpAddress"] == "10.0.0.1"
        assert result["publicIpAddress"] == ""
        assert (
            result["launchtime"] == 1704088800
        )  # UTC timestamp for 2024-01-01 00:00:00
        assert result["message"] == "Deployed in namespace: test-namespace"


def test_extract_pod_details_no_launch_time():
    """Test _extract_pod_details function when launch_time is None."""
    pod = {
        "metadata": {
            "uid": "test-uid",
            "name": "test-name",
            "namespace": "test-namespace",
        },
        "status": {"phase": "running", "pod_ip": "10.0.0.1"},
    }
    with patch(
        "gke_provider.commands.get_request_machine_status._map_pod_results",
        return_value=("running", "succeed"),
    ):
        result = get_request_machine_status._extract_pod_details(pod)
        assert result["machineId"] == "test-uid"
        assert result["name"] == "test-name"
        assert result["result"] == "succeed"
        assert result["status"] == "running"
        assert result["privateIpAddress"] == "10.0.0.1"
        assert result["publicIpAddress"] == ""
        assert result["launchtime"] == ""
        assert result["message"] == "Deployed in namespace: test-namespace"


def test_map_pod_results_pending():
    """Test _map_pod_results when pod phase is pending."""
    pod = {"status": {"phase": "pending"}}
    status, result = get_request_machine_status._map_pod_results(pod)
    assert status == get_request_machine_status.POD_STATUS_RUNNING
    assert result == get_request_machine_status.POD_RESULT_EXECUTING


def test_map_pod_results_running():
    """Test _map_pod_results when pod phase is running."""
    pod = {"status": {"phase": "running"}}
    status, result = get_request_machine_status._map_pod_results(pod)
    assert status == get_request_machine_status.POD_STATUS_RUNNING
    assert result == get_request_machine_status.POD_RESULT_SUCCEED


def test_map_pod_results_succeeded():
    """Test _map_pod_results when pod phase is succeeded."""
    pod = {"status": {"phase": "succeeded"}}
    status, result = get_request_machine_status._map_pod_results(pod)
    assert status == get_request_machine_status.POD_STATUS_STOPPED
    assert result == get_request_machine_status.POD_RESULT_SUCCEED


def test_map_pod_results_failed():
    """Test _map_pod_results when pod phase is failed."""
    pod = {"status": {"phase": "failed"}}
    status, result = get_request_machine_status._map_pod_results(pod)
    assert status == get_request_machine_status.POD_STATUS_TERMINATED
    assert result == get_request_machine_status.POD_RESULT_FAIL


def test_map_pod_results_unknown():
    """Test _map_pod_results when pod phase is unknown."""
    pod = {"status": {"phase": "unknown"}}
    status, result = get_request_machine_status._map_pod_results(pod)
    assert status == get_request_machine_status.POD_STATUS_TERMINATED
    assert result == get_request_machine_status.POD_RESULT_FAIL


def test_map_pod_results_default():
    """Test _map_pod_results when pod phase is not in map."""
    pod = {"status": {"phase": "other"}}
    status, result = get_request_machine_status._map_pod_results(pod)
    assert status == get_request_machine_status.POD_STATUS_TERMINATED
    assert result == get_request_machine_status.POD_RESULT_FAIL


def test_map_pod_results_none():
    """Test _map_pod_results when pod is None."""
    pod = None
    status, result = get_request_machine_status._map_pod_results(pod)
    assert status == "unknown"
    assert result == "unknown"
