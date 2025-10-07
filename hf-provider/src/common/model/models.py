from typing import Any, Optional, Union

from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self


class Template(BaseModel):
    templateId: str = Field(
        ...,
        description="(mandatory) Unique ID that can identify this template in the cloud provider",
    )
    machineCount: int = Field(
        ...,
        description="(mandatory) Number of hosts of this template to be provisioned",
    )


class HFGetAvailableTemplates(BaseModel):
    templates: Optional[list[Any]]


class HFGetAvailableTemplatesResponse(BaseModel):
    message: Optional[str] = Field(
        default=None,
        description="(optional) Any additional message the caller should know",
    )
    templates: list[Any]


class HFRequestMachines(BaseModel):
    template: Template = Field(
        ...,
        description="(mandatory) Using the Template class to request machine provisioning",
    )


class HFResponseWithMessage(BaseModel):
    message: Optional[str] = Field(
        default=None,
        description="(optional) Any additional message the caller should know",
    )


class HFResponseWithRequestId(BaseModel):
    requestId: str = Field(
        ...,
        description="(mandatory) Unique ID to identify this request in the cloud provider",
    )


class HFRequestMachinesResponse(HFResponseWithMessage, HFResponseWithRequestId):
    pass


class HFRequestReturnMachines(BaseModel):
    class Machine(BaseModel):
        name: str = Field(
            ..., description="Host name of the machine that must be returned"
        )

    machines: Union[list[Machine], Machine] = Field(
        ...,
        description="(mandatory) List of machine objects, each containing the hostname",
    )


class HFRequestReturnMachinesResponse(HFResponseWithMessage, HFResponseWithRequestId):
    pass


class HFRequestStatus(BaseModel):
    requests: Union[list[dict[str, str]], dict[str, str]] = Field(
        ...,
        description="(mandatory) Unique ID to identify this request in the cloud provider.",
    )


class HFRequestStatusResponse(HFResponseWithMessage):
    class Request(HFResponseWithRequestId):
        class Machine(HFResponseWithMessage):
            machineId: str = Field(
                ..., description="ID of the machine being retrieved from provider"
            )
            name: str = Field(..., description="Host name of the machine")
            result: str = Field(
                ...,
                description=(
                    (
                        "Status of this request related to this machine. Possible values:  "
                        "'executing', 'fail', 'succeed'."
                    )
                    + (
                        " For example, call requestMachines with templateId and machineCount 3, "
                        "and then call"
                    )
                    + (
                        " getRequestStatus to check the status of this request. We should get 3 "
                        "machines with result"
                    )
                    + (
                        " 'succeed'. If any machine is missing or the status is not correct, "
                        "that machine is not usable."
                    )
                ),
            )
            status: Optional[str] = Field(
                default=None,
                description=(
                    "Status of machine. Expected values: running, stopped, terminated, "
                    "shutting-down, stopping."
                ),
            )
            privateIpAddress: Optional[str] = Field(
                default=None, description="private IP address of the machine"
            )
            publicIpAddress: Optional[str] = Field(
                default=None, description="public IP address of the machine"
            )
            launchTime: int = Field(
                ..., description="Launch time of the machine in seconds (UTC format)"
            )

        status: str = Field(
            ...,
            description=(
                "Status of request. Possible values: 'running', 'complete', "
                "'complete_with_error'. You should check the"
                + "machine information, if any, when the value is 'complete' or "
                "'complete_with_error'"
            ),
        )
        machines: Union[Machine, list[Machine]]

    requests: Union[Request, list[Request]] = Field(
        ..., description="The requests with their states"
    )


class HFReturnRequests(BaseModel):
    machines: Optional[Union[list[str], list[dict[str, str]]]] = Field(
        default=None,
        description="(mandatory) 'All' or a list of hostnames of the machine to get status",
    )


class HFReturnRequestsResponse(HFResponseWithMessage):
    class Request(BaseModel):
        machine: str = Field(
            ..., description="Host name of the machine that must be returned"
        )
        gracePeriod: int = Field(
            default=0,
            description=(
                "Time remaining (in seconds) before this host will be reclaimed by the provider"
            ),
        )

    requests: Union[Request, list[Request]] = Field(
        default=[],
        description=(
            "[Note: Includes Spot instances and On-Demand instances"
            "returned from the management console]"
        ),
    )


class HFRequest(BaseModel):
    requestMachines: Optional[HFRequestMachines] = Field(
        None, description="Request to provision machines"
    )
    requestReturnMachines: Optional[HFRequestReturnMachines] = Field(
        None, description="Request to return machines"
    )
    requestStatus: Optional[HFRequestStatus] = Field(
        None, description="Request for machine provisioning status"
    )
    returnRequests: Optional[HFReturnRequests] = Field(
        None,
        description="Request to the status for a previous return machines requests",
    )
    pod_spec: Optional[dict] = Field(
        None,
        description="Kubernetes Pod specification (required with requestMachines)",
    )

    @model_validator(mode="before")
    def check_mutually_exclusive(cls: Self, values: dict) -> Any:
        has_machines = values.get("requestMachines") is not None
        has_return_machines = values.get("requestReturnMachines") is not None
        has_status = values.get("requestStatus") is not None
        has_return_requests = values.get("returnRequests") is not None

        if (
            sum([has_machines, has_return_machines, has_status, has_return_requests])
            != 1
        ):
            raise ValueError(
                "Exactly one of requestMachines, requestReturnMachines, "
                "requestStatus, or returnRequests must be present."
            )

        if has_machines and values.get("pod_spec") is None:
            raise ValueError("pod_spec is required when requestMachines is present.")

        if has_return_requests:
            machines = values.get("machines")
            if machines is not None and not machines:
                raise ValueError("If machines field is provided, it cannot be empty")

        return values
