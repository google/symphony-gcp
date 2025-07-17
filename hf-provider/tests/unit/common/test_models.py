from common.model import models
from unittest.mock import MagicMock
import pytest


def test_template_model():
    """Test the Template model."""
    template = models.Template(templateId="test-id", machineCount=2)
    assert template.templateId == "test-id"
    assert template.machineCount == 2


def test_hfrequestmachines_model():
    """Test the HFRequestMachines model."""
    template = models.Template(templateId="test-id", machineCount=2)
    hfr_machines = models.HFRequestMachines(template=template)
    assert hfr_machines.template == template


def test_hfrequest_model_valid():
    """Test the HFRequest model with valid data."""
    template = models.Template(templateId="test-id", machineCount=2)
    hfr_machines = models.HFRequestMachines(template=template)
    hfr = models.HFRequest(requestMachines=hfr_machines, pod_spec={"test": "spec"}) # type: ignore
    assert hfr.requestMachines == hfr_machines
    assert hfr.pod_spec == {"test": "spec"}


def test_hfrequest_model_mutually_exclusive_error():
    """Test the HFRequest model with mutually exclusive error."""
    with pytest.raises(ValueError):
        models.HFRequest(requestMachines=MagicMock(), requestReturnMachines=MagicMock()) # type: ignore


def test_hfrequest_model_podspec_required_error():
    """Test the HFRequest model with pod_spec required error."""
    template = models.Template(templateId="test-id", machineCount=2)
    hfr_machines = models.HFRequestMachines(template=template)
    with pytest.raises(ValueError):
        models.HFRequest(requestMachines=hfr_machines) # type: ignore
