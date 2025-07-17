import datetime

import pytest
from gcp_symphony_operator.api.v1.types.gcp_symphony_resource import (
    Condition,
    GCPSymphonyResource,
    GCPSymphonyResourceSpec,
    GCPSymphonyResourceStatus,
    MachineStatus,
    ReturnedMachine,
)
from pydantic import ValidationError


def test_gcpsymphonyresourcespec_valid() -> None:
    """Test GCPSymphonyResourceSpec with valid data."""
    data = {
        "podSpec": {"containers": [{"name": "test-container", "image": "test-image"}]},
        "machineCount": 2,
        "namePrefix": "test-prefix",
        "labels": {"test-label": "test-value"},
        "annotations": {"test-annotation": "test-value"},
        "default_grace_period": 60,
    }
    spec = GCPSymphonyResourceSpec(**data)
    assert spec.podSpec == data["podSpec"]
    assert spec.machineCount == data["machineCount"]
    assert spec.namePrefix == data["namePrefix"]
    assert spec.labels == data["labels"]
    assert spec.annotations == data["annotations"]
    assert spec.default_grace_period == data["default_grace_period"]


def test_gcpsymphonyresourcespec_missing_podspec() -> None:
    """Test GCPSymphonyResourceSpec with missing podSpec."""
    data = {
        "machineCount": 2,
        "namePrefix": "test-prefix",
        "labels": {"test-label": "test-value"},
        "annotations": {"test-annotation": "test-value"},
        "default_grace_period": 60,
    }
    with pytest.raises(ValidationError):
        GCPSymphonyResourceSpec(**data)


def test_gcpsymphonyresourcespec_invalid_machinecount() -> None:
    """Test GCPSymphonyResourceSpec with invalid machineCount."""
    data = {
        "podSpec": {"containers": [{"name": "test-container", "image": "test-image"}]},
        "machineCount": -1,
        "namePrefix": "test-prefix",
        "labels": {"test-label": "test-value"},
        "annotations": {"test-annotation": "test-value"},
        "default_grace_period": 60,
    }
    with pytest.raises(ValidationError):
        GCPSymphonyResourceSpec(**data)


def test_condition_valid() -> None:
    """Test Condition with valid data."""
    data = {
        "type": "TestType",
        "status": "True",
        "lastTransitionTime": "2024-01-01T00:00:00Z",
        "reason": "TestReason",
        "message": "Test Message",
    }
    condition = Condition(**data)
    assert condition.type == data["type"]
    assert condition.status == data["status"]
    assert condition.lastTransitionTime == data["lastTransitionTime"]
    assert condition.reason == data["reason"]
    assert condition.message == data["message"]


def test_machinestatus_valid() -> None:
    """Test MachineStatus with valid data."""
    data = {
        "phase": "Running",
        "lastTransitionTime": "2024-01-01T00:00:00Z",
        "reason": "TestReason",
        "message": "Test Message",
        "hostIP": "127.0.0.1",
        "podIP": "10.0.0.1",
    }
    status = MachineStatus(**data)
    assert status.phase == data["phase"]
    assert status.lastTransitionTime == data["lastTransitionTime"]
    assert status.reason == data["reason"]
    assert status.message == data["message"]
    assert status.hostIP == data["hostIP"]
    assert status.podIP == data["podIP"]


def test_returned_machine_valid() -> None:
    """Test ReturnedMachine with valid data."""
    data = {
        "name": "test-machine",
        "returnRequestId": "test-request-id",
        "returnRequestTime": datetime.datetime.now(datetime.timezone.utc),
    }
    returned_machine = ReturnedMachine(**data)
    assert returned_machine.name == data["name"]
    assert returned_machine.returnRequestId == data["returnRequestId"]
    assert returned_machine.returnRequestTime == data["returnRequestTime"]


def test_returned_machine_invalid_timezone() -> None:
    """Test ReturnedMachine with invalid timezone."""
    data = {
        "name": "test-machine",
        "returnRequestId": "test-request-id",
        "returnRequestTime": datetime.datetime.now(),  # No timezone
    }
    with pytest.raises(ValidationError):
        ReturnedMachine(**data)


def test_gcpsymphonyresourcestatus_valid() -> None:
    """Test GCPSymphonyResourceStatus with valid data."""
    returned_machine = ReturnedMachine(
        name="test-machine",
        returnRequestId="test-request-id",
        returnRequestTime=datetime.datetime.now(datetime.timezone.utc),
    )
    data = {
        "phase": "Running",
        "availableMachines": 2,
        "conditions": [{"type": "TestType", "status": "True"}],
        "returnedMachines": [returned_machine],
    }
    status = GCPSymphonyResourceStatus(**data)
    assert status.phase == data["phase"]
    assert status.availableMachines == data["availableMachines"]
    assert len(status.conditions) == 1 if isinstance(status.conditions, list) else False
    assert (
        len(status.returnedMachines) == 1
        if isinstance(status.returnedMachines, list)
        else False
    )


def test_gcpsymphonyresource_valid() -> None:
    """Test GCPSymphonyResource with valid data."""
    metadata = {"name": "test-resource", "namespace": "test-namespace"}
    spec_data = {
        "podSpec": {"containers": [{"name": "test-container", "image": "test-image"}]},
        "machineCount": 2,
        "namePrefix": "test-prefix",
    }
    spec = GCPSymphonyResourceSpec(**spec_data)
    data = {
        "metadata": metadata,
        "spec": spec,
    }
    resource = GCPSymphonyResource(**data)
    # apiVersion and kind are set by default factories
    assert resource.apiVersion is not None
    assert resource.kind is not None
    assert resource.metadata == data["metadata"]
    assert resource.spec == spec
