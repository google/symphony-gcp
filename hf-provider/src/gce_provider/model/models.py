from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from common.model.models import HFRequestMachines
from gce_provider.utils.constants import MachineResult, MachineStatus


class HFGceRequestMachines(HFRequestMachines):
    gcp_zone: str = Field(
        ..., description="(mandatory) Specify the GCP zone to request the machine"
    )
    gcp_instance_group: str = Field(
        ...,
        description="(mandatory) The instance group manager ID to request a machine from",
    )


class ResourceIdentifier(BaseModel):
    project: str = Field(..., description="(mandatory) Specify the project ID)")
    zone: str = Field(..., description="(mandatory) Specify the zone)")
    name: str = Field(..., description="(mandatory) Specify the instance name)")
    resourceType: Optional[str] = Field(default=None, description="The type of the resource")


class InstanceIps(BaseModel):
    name: str = Field(..., description="(mandatory) Specify the instance name)")
    internal_ip: Optional[str] = Field(
        ..., description="(mandatory) Specify the instance's internal IP)"
    )
    external_ip: Optional[str] = Field(
        ..., description="(mandatory) Specify the instance's external IP)"
    )


class HfMachine(BaseModel):
    machine_name: str = Field(..., description="(mandatory) The name of the machine")
    request_id: str = Field(
        ..., description="(mandatory) The ID of the request that invoked the machine"
    )
    operation_id: str = Field(
        ...,
        description="(mandatory) The Google Cloud operation that requested the machine",
    )
    return_request_id: Optional[str] = Field(
        default=None,
        description="The ID of the return request that invoked deletion of this machine",
    )
    delete_operation_request_id: Optional[str] = Field(
        default=None,
        description="The unique request ID of the delete operation for this machine",
    )
    delete_operation_id: Optional[str] = Field(
        default=None,
        description="The Google Cloud operation that deleted the machine",
    )
    machine_state: int = Field(
        ...,
        description="(mandatory) The current machine state represented by Google Cloud",
    )
    gcp_zone: str = Field(
        ..., description="(mandatory) The GCP zone in which the machine is deployed"
    )
    instance_group_manager: str = Field(
        ..., description="(mandatory) The GCP Instance Group that manages this machine"
    )
    internal_ip: Optional[str] = Field(
        default=None, description="The internal IP address of the machine"
    )
    external_ip: Optional[str] = Field(
        default=None, description="The external IP address of the machine"
    )
    created_at: datetime = Field(..., description="The timestamp the machine record was created")
    updated_at: Optional[datetime] = Field(
        default=None, description="The timestamp the machine record was last updated"
    )


class HfMachineStatus(HfMachine):
    hf_machine_status: Optional[MachineStatus] = Field(
        default=None,
        description="The machine status, in the context of a getRequestStatus request",
    )
    hf_machine_result: Optional[MachineResult] = Field(
        default=None,
        description="The machine result, in the context of a getRequestStatus request",
    )
