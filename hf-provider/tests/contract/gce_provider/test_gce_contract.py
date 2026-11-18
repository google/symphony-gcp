import json

import pytest
from contract.driver import assert_matches_schema, resource_payload

SAMPLE_TEMPLATES = "get-available-templates/get-available-templates-001.json"
SAMPLE_STATUS_LIST_FORM = "get-request-status/get-request-status-001.json"
SAMPLE_STATUS_OBJECT_FORM = "get-request-status/get-request-status-002.json"
SAMPLE_RETURN_REQUESTS = "get-return-requests/get-return-requests-001.json"
SAMPLE_REQUEST_MACHINES = "request-machines/request-machines-001.json"

REQUEST_RETURN_PAYLOAD = {"machines": [{"name": "contract-nonexistent-host"}]}


def _assert_clean_json(result):
    """Check for exit 0, empty stderr, and JSON on stdout."""
    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"
    assert result.stderr == "", f"stderr not empty: {result.stderr}"
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"stdout is not pure JSON: {exc}\nstdout: {result.stdout!r}") from exc


def test_get_available_templates(gce_cli):
    """getAvailableTemplates reads the templates from the configuration file."""
    result = gce_cli.run("getAvailableTemplates", payload_path=resource_payload(SAMPLE_TEMPLATES))

    parsed = _assert_clean_json(result)
    assert "templates" in parsed
    assert gce_cli.log_file.exists()
    assert_matches_schema(parsed, "gce_provider/get_available_templates.json")


@pytest.mark.parametrize(
    "sample",
    [SAMPLE_STATUS_LIST_FORM, SAMPLE_STATUS_OBJECT_FORM],
    ids=["list-form", "object-form"],
)
def test_get_request_status_accepts_both_request_forms(gce_cli, sample):
    """getRequestStatus accepts the requests field as a list of objects or one object."""
    gce_cli.initialize_db()

    result = gce_cli.run("getRequestStatus", payload_path=resource_payload(sample))

    parsed = _assert_clean_json(result)
    assert_matches_schema(parsed, "gce_provider/get_request_status.json")


def test_get_request_status_with_machines(gce_cli, seeded_request):
    """getRequestStatus reports the machine data from the database."""
    result = gce_cli.run("getRequestStatus", payload={"requests": [{"requestId": seeded_request}]})

    parsed = _assert_clean_json(result)
    machines = parsed["requests"][0]["machines"]
    assert len(machines) == 1, f"expected the seeded machine, got: {parsed}"
    assert_matches_schema(parsed, "gce_provider/get_request_status.json")


def test_get_return_requests(gce_cli):
    """getReturnRequests with no machines to report."""
    gce_cli.initialize_db()

    result = gce_cli.run("getReturnRequests", payload_path=resource_payload(SAMPLE_RETURN_REQUESTS))

    parsed = _assert_clean_json(result)
    assert_matches_schema(parsed, "gce_provider/get_return_requests.json")


@pytest.mark.usefixtures("seeded_returned_machine")
def test_get_return_requests_with_machines(gce_cli):
    """getReturnRequests reports a deleted machine as a return request."""
    result = gce_cli.run("getReturnRequests", payload_path=resource_payload(SAMPLE_RETURN_REQUESTS))

    parsed = _assert_clean_json(result)
    assert len(parsed["requests"]) == 1, f"expected the returned machine, got: {parsed}"
    assert_matches_schema(parsed, "gce_provider/get_return_requests.json")


def test_request_machines_success(gce_cli):
    """requestMachines gives a request id."""
    result = gce_cli.run(
        "requestMachines",
        payload_path=resource_payload(SAMPLE_REQUEST_MACHINES),
        stubbed=True,
    )

    parsed = _assert_clean_json(result)
    assert_matches_schema(parsed, "gce_provider/request_machines.json")


def test_request_return_machines_success(gce_cli):
    """requestReturnMachines gives a request id even for an unknown machine."""
    gce_cli.initialize_db()

    result = gce_cli.run("requestReturnMachines", payload=REQUEST_RETURN_PAYLOAD, stubbed=True)

    parsed = _assert_clean_json(result)
    assert_matches_schema(parsed, "gce_provider/request_return_machines.json")


@pytest.mark.parametrize(
    "command",
    ["requestMachines", "requestReturnMachines", "getRequestStatus", "getReturnRequests"],
)
def test_failure_is_clean(gce_cli, command):
    """A bad payload exits 1 with the error on stdout."""
    result = gce_cli.run(command, payload={})

    assert result.returncode == 1, f"stdout: {result.stdout}\nstderr: {result.stderr}"
    assert result.stdout.startswith("Error:")
    assert result.stderr == "", f"stderr not empty: {result.stderr}"
    assert "Traceback" in gce_cli.log_file.read_text()


def test_a_raised_warning_lands_in_the_log_not_stderr(gce_cli):
    """A warning raised mid-command goes to the log, not stderr (#86)."""
    result = gce_cli.run(
        "requestMachines",
        payload_path=resource_payload(SAMPLE_REQUEST_MACHINES),
        stubbed=True,
    )

    _assert_clean_json(result)
    assert "contract-canary" in gce_cli.log_file.read_text()
