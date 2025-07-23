import datetime
from functools import lru_cache
from typing import Any, Dict, List, Optional

from gcp_symphony_operator.config import (  # Import the Config class from the config module
    Config,
    get_config_sync,
)
from pydantic import BaseModel, Field, field_validator


# Factory functions to get config values at runtime
@lru_cache(maxsize=1)
def _get_api_version():
    try:
        config = get_config_sync(thin=True)
        return f"{config.crd_group}/{config.crd_api_version}"
    except Exception:
        return f"{Config.DEFAULT_CRD_GROUP}/{Config.DEFAULT_CRD_API_VERSION}"


@lru_cache(maxsize=1)
def _get_kind():
    try:
        config = get_config_sync(thin=True)
        return config.crd_kind
    except Exception:
        return Config.DEFAULT_CRD_KIND


class GCPSymphonyResourceSpec(BaseModel):
    """Specification for the GCPSymphonyResource custom resource."""

    podSpec: Dict[str, Any] = Field(
        ..., description="(mandatory) A complete Kubernetes PodSpec"
    )
    machineCount: Optional[int] = Field(
        default=1,
        ge=0,
        description="(optional) Number of machines (pods) to provision. Default is 1.",
    )
    namePrefix: str = Field(
        ...,
        description="(mandatory) Prefix for the name of the machines (pods) to provision",
    )
    labels: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="(optional) Labels to add to the machines (pods) to provision",
    )
    annotations: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="(optional) Annotations to add to the machines (pods) to provision",
    )
    default_grace_period: Optional[int] = Field(
        default=30,
        ge=0,
        description="(optional) Default grace period for the machines (pods) to terminate",
    )


class Condition(BaseModel):
    """Condition in the status."""

    type: str
    status: str
    lastTransitionTime: Optional[str] = None
    reason: Optional[str] = None
    message: Optional[str] = None


class ReturnedMachine(BaseModel):
    """Deleted machine (pod) information."""

    returnRequestId: Optional[str] = Field(
        None,
        description=(
            "ID of the return request that was used to delete the machine (pod). "
            "If this value is None, the machine (pod) was deleted without a return request."
        ),
    )
    returnTime: datetime.datetime = Field(
        ...,
        description="Time when the return request was made",
        json_schema_extra={"format": "date-time"},
    )
    name: Optional[str] = Field(
        None, description="Hostname of the deleted machine (pod)"
    )

    @field_validator("returnTime")
    @classmethod
    def validate_timezone(cls, v: datetime.datetime):
        if v.tzinfo is None:
            raise ValueError(
                "returnTime of the ReturneMachine class"
                "must include timezone information"
            )
        return v


class MachineStatus(BaseModel):
    """Status of an individual machine (pod)."""

    phase: Optional[str] = None
    lastTransitionTime: Optional[str] = None
    reason: Optional[str] = None
    message: Optional[str] = None
    hostIP: Optional[str] = None
    podIP: Optional[str] = None


class GCPSymphonyResourceStatus(BaseModel):
    """Status for the GCPSymphonyResource custom resource."""

    phase: str = Field("Unknown", description="The phase of the custom resource")
    availableMachines: int = Field(0, description="The number of available Machines")
    conditions: Optional[List[Condition]] = Field(
        default_factory=list, description="Conditions of the custom resource"
    )
    returnedMachines: Optional[List[ReturnedMachine]] = Field(
        default_factory=list,
        description=("When pod (machine) is deleted, it will be placed on this list."),
    )


class GCPSymphonyResource(BaseModel):
    """GCPSymphonyResource custom resource."""

    apiVersion: str = Field(default_factory=_get_api_version)
    kind: str = Field(default_factory=_get_kind)
    metadata: Dict[str, Any]
    spec: GCPSymphonyResourceSpec
    status: Optional[GCPSymphonyResourceStatus] = None
