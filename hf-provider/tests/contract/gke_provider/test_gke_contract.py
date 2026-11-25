import json

import pytest
from contract.driver import assert_matches_schema, resource_payload

SAMPLE_TEMPLATES = "get-available-templates/get-available-templates-001.json"
SAMPLE_STATUS_LIST_FORM = "get-request-status/get-request-status-001.json"
SAMPLE_STATUS_OBJECT_FORM = "get-request-status/get-request-status-002.json"
SAMPLE_RETURN_REQUESTS = "get-return-requests/get-return-requests-001.json"
SAMPLE_REQUEST_MACHINES = "request-machines/request-machines-001.json"

REQUEST_RETURN_PAYLOAD = {"machines": [{"name": "contract-nonexistent-host"}]}

# An empty getReturnRequests payload asks for all machines.
_BAD_PAYLOAD_BY_COMMAND = {
    "requestMachines": {},
    "requestReturnMachines": {},
    "getRequestStatus": {},
    "getReturnRequests": {"machines": 5},
}


def _assert_clean_json(result):
    """Check for exit 0, empty stderr, and JSON on stdout."""
    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"
    assert result.stderr == "", f"stderr not empty: {result.stderr}"
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"stdout is not pure JSON: {exc}\nstdout: {result.stdout!r}") from exc


def test_get_available_templates(gke_cli):
    """getAvailableTemplates reads the templates from the configuration file."""
    result = gke_cli.run("getAvailableTemplates", payload_path=resource_payload(SAMPLE_TEMPLATES))

    parsed = _assert_clean_json(result)
    assert "templates" in parsed
    assert gke_cli.log_file.exists()
    assert_matches_schema(parsed, "gke_provider/get_available_templates.json")


@pytest.mark.parametrize(
    "sample",
    [SAMPLE_STATUS_LIST_FORM, SAMPLE_STATUS_OBJECT_FORM],
    ids=["list-form", "object-form"],
)
def test_get_request_status_accepts_both_request_forms(gke_cli, sample):
    """getRequestStatus accepts the requests field as a list of objects or one object."""
    result = gke_cli.run("getRequestStatus", payload_path=resource_payload(sample), stubbed=True)

    parsed = _assert_clean_json(result)
    assert_matches_schema(parsed, "gke_provider/get_request_status.json")


def test_get_request_status_with_machines(gke_cli, seeded_request):
    """getRequestStatus reports a running pod from the cluster."""
    result = gke_cli.run(
        "getRequestStatus",
        payload={"requests": [{"requestId": seeded_request}]},
        stubbed=True,
    )

    parsed = _assert_clean_json(result)
    machines = parsed["requests"][0]["machines"]
    assert len(machines) == 1, f"expected the seeded machine, got: {parsed}"
    assert_matches_schema(parsed, "gke_provider/get_request_status.json")


def test_get_request_status_with_pending_machine(gke_cli, pending_request):
    """getRequestStatus reports a pod that has no IP or start time yet."""
    result = gke_cli.run(
        "getRequestStatus",
        payload={"requests": [{"requestId": pending_request}]},
        stubbed=True,
    )

    parsed = _assert_clean_json(result)
    assert parsed["requests"][0]["status"] == "running", f"got: {parsed}"
    assert_matches_schema(parsed, "gke_provider/get_request_status.json")


def test_get_request_status_for_return_request(gke_cli, seeded_return_request):
    """getRequestStatus reports a return request."""
    result = gke_cli.run(
        "getRequestStatus",
        payload={"requests": [{"requestId": seeded_return_request}]},
        stubbed=True,
    )

    parsed = _assert_clean_json(result)
    assert parsed["requests"][0]["status"] == "complete", f"got: {parsed}"
    assert_matches_schema(parsed, "gke_provider/get_request_status.json")


def test_get_return_requests(gke_cli):
    """getReturnRequests with no machines to report."""
    result = gke_cli.run(
        "getReturnRequests",
        payload_path=resource_payload(SAMPLE_RETURN_REQUESTS),
        stubbed=True,
    )

    parsed = _assert_clean_json(result)
    assert_matches_schema(parsed, "gke_provider/get_return_requests.json")


def test_get_return_requests_with_machines(gke_cli, seeded_returned_machine):
    """getReturnRequests reports a returned machine as a return request."""
    result = gke_cli.run(
        "getReturnRequests",
        payload={"machines": [{"name": seeded_returned_machine}]},
        stubbed=True,
    )

    parsed = _assert_clean_json(result)
    assert len(parsed["requests"]) == 1, f"expected the returned machine, got: {parsed}"
    assert_matches_schema(parsed, "gke_provider/get_return_requests.json")


def test_request_machines_success(gke_cli):
    """requestMachines gives a request id."""
    result = gke_cli.run(
        "requestMachines",
        payload_path=resource_payload(SAMPLE_REQUEST_MACHINES),
        stubbed=True,
    )

    parsed = _assert_clean_json(result)
    assert_matches_schema(parsed, "gke_provider/request_machines.json")


def test_request_return_machines_success(gke_cli):
    """requestReturnMachines gives a request id even for an unknown machine."""
    result = gke_cli.run("requestReturnMachines", payload=REQUEST_RETURN_PAYLOAD, stubbed=True)

    parsed = _assert_clean_json(result)
    assert_matches_schema(parsed, "gke_provider/request_return_machines.json")


@pytest.mark.parametrize(
    ("command", "payload"),
    list(_BAD_PAYLOAD_BY_COMMAND.items()),
    ids=list(_BAD_PAYLOAD_BY_COMMAND),
)
def test_failure_is_clean(gke_cli, command, payload):
    """A bad payload exits 1 with the error on stdout."""
    result = gke_cli.run(command, payload=payload, stubbed=True)

    assert result.returncode == 1, f"stdout: {result.stdout}\nstderr: {result.stderr}"
    assert result.stdout.startswith("Error:")
    assert result.stderr == "", f"stderr not empty: {result.stderr}"
    assert "Traceback" in gke_cli.log_file.read_text()


def test_a_raised_warning_lands_in_the_log_not_stderr(gke_cli):
    """A warning raised mid-command goes to the log, not stderr (#86)."""
    result = gke_cli.run(
        "requestMachines",
        payload_path=resource_payload(SAMPLE_REQUEST_MACHINES),
        stubbed=True,
    )

    _assert_clean_json(result)
    assert "contract-canary" in gke_cli.log_file.read_text()
