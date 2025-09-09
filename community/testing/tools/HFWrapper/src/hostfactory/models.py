from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import List, Literal, Optional

from pydantic import BaseModel, RootModel, field_validator, model_validator


@dataclass
class HostFactoryAPI:
    service_configuration = "/service/configuration"
    providers = "/providers"
    provider = "/provider"
    requestors = "/requestors"
    requestor = "/requestor"
    scheduled_requests = "/scheduleddemandrequests"
    request_instance = "/demandrequests"
    hosts = "/hosts"
    requests = "/requests"
    templates = "/templates"


class HFServiceConfiguration(BaseModel):
    HF_LOGLEVEL: str = "LOG_INFO"
    HF_LOG_MAX_FILE_SIZE: int = 10
    HF_LOG_MAX_ROTATE: int = 5
    HF_REQUESTOR_POLL_INTERVAL: int = 30
    HF_HOUSEKEEPING_LOOP_INTERVAL: int = 30
    HF_REST_TRANSPORT: str = "TCPIPv4"
    HF_REST_LISTEN_PORT: int = 9080
    HF_REQUESTOR_ACTION_TIMEOUT: int = 240
    HF_PROVIDER_ACTION_TIMEOUT: int = 300
    HF_DB_HISTORY_DURATION: int = 90
    HF_REST_RESULT_DEFAULT_PAGESIZE: int = 2000
    HF_REST_RESULT_MAX_PAGESIZE: int = 10000
    HF_DEMAND_BATCH_LIMIT: int = 100
    HF_RETURN_BATCH_LIMIT: int = 100


class HFRequest_end(BaseModel):
    dateTime: Optional[str] = None  # End of the request. Not supported for recurring.
    duration: Optional[str] = (
        None  # ISO 8601 format with at least one minute up to 10 years.
    )

    @field_validator("dateTime", mode="before")
    @classmethod
    def transform(cls, raw):
        if isinstance(raw, datetime.datetime):
            return raw.strftime("%Y%m%dT%H%M%SZ")
        return raw


class HFRequest_start(BaseModel):
    dateTime: str = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ",
    )

    @field_validator("dateTime", mode="before")
    @classmethod
    def transform(cls, raw):
        if isinstance(raw, datetime.datetime):
            return raw.strftime("%Y%m%dT%H%M%SZ")
        return raw


class HFRequest_recurrence(BaseModel):
    """For a recurring scheduled request, the recurrence formula to indicate the frequency (daily or weekly) that the request should recur.

    Recurrence cannot run indefinitely; indicate the maximum point for the recurrence using the UNTIL or COUNT options). One option must be specified, and use only one option as multiple formulas are not supported.

    The UNTIL value must be specified in UTC time; use Z to indicate UTC time. The maximum UNTIL value is ten years.

    The maximum COUNT value is 5000.
    """

    RRULE: str
    overlapAction: Literal["close", "allow"]


class HFRequest_units_minimum(BaseModel):
    ncores: int
    nram: Optional[int]


class HFRequest_demand_resource(BaseModel):
    nunits: int
    units_minimum: HFRequest_units_minimum


class HFRequest_demand_hosts(BaseModel):
    prov_name: str  # Provider instance name
    template_name: str
    ninstances: int  # Number of requested instances
    start: Optional[HFRequest_start] = (
        None  # Start of the request, if recurring then start of first request
    )
    end: Optional[HFRequest_end] = None  # End of the request
    unit_minimum: Optional[HFRequest_units_minimum] = None


class HFRequest(BaseModel):
    """- request_name: 128 characters [number, upper-case letters, lower-case letters, dash (-), underscore (_)]
    - request_comments: 256 characters
    - prov_name: Provider instance name
    - template_name:
    - ninstances: Number of requested instances
    - start: Start of the request, if recurring then start of first request.
    - end: End of the request. Not supported for recurring.
    - recurrence: Recurrence configuration.
    - overlapAction: Allow or not the overlap of requests if previous request is not complete.
    """

    request_name: Optional[str] = None
    request_comments: Optional[str] = None  # 256 char
    demand_resource: Optional[List[HFRequest_demand_resource]] = (
        None  # Request recurrence
    )
    demand_hosts: Optional[List[HFRequest_demand_hosts]] = None

    @model_validator(mode="before")
    @classmethod
    def check_unique_request_type(cls, data: dict):
        resource = data.get("demand_resource")
        hosts = data.get("demand_hosts")
        if (resource is None and hosts is None) or (
            resource is not None and hosts is not None
        ):
            raise Exception(
                "Either one of demand_resource and demand_hosts should be set",
            )
        return data


class HFRequestStatus(BaseModel):
    reqName: Optional[str] = None
    status: Optional[
        Literal["Created", "Active", "Closing", "Closed"]
    ] = None
    requestId: Optional[str] = None
    requestName: Optional[str] = None
    createTime: Optional[str] = None
    startTimeOfFirstDemand: Optional[int] = None
    lastSubmittedTime: Optional[int] = None
    nextSubmissionTime: Optional[int] = None
    hfcsrftoken: Optional[str] = None
    sortBy: Optional[str] = None
    sortOrder: Optional[bool] = None
    pageSize: Optional[int] = None
    startIndex: Optional[int] = None


class HFDeleteRequest_request(BaseModel):
    id: str
    close_instances: bool


class HFDeleteRequest(RootModel):
    root: List[HFDeleteRequest_request]


class HFRequestInstances(BaseModel):
    reqName: Optional[str] = None
    status: Optional[
        Literal["Created", "Running", "Provisioned", "Closing", "Closed"]
    ] = None
    requestId: Optional[str] = None
    scheduledRequestId: Optional[str] = None
    requestName: Optional[str] = None
    startTime: Optional[str] = None
    hfcsrftoken: Optional[str] = None
    sortBy: Optional[str] = None
    sortOrder: Optional[bool] = None
    pageSize: Optional[int] = None
    startIndex: Optional[int] = None


class HFDeleteRequestInstances(RootModel):
    root: List[str]

class HFCloudHosts(BaseModel):
    requestId: Optional[str] = None #  String	Optional	ID of the scale-out request. To view hosts provisioned for multiple request IDs, specify a comma-separated list of request IDs (for example, &requestId=1114,1115).
    requestName: Optional[str] = None #  String	Optional	Name of the scale-out request. To view hosts provisioned with specific request names, specify a comma-separated list of request names (for example, &requestName=LoB1_AppA,LoB1_AppB).
    reqName: Optional[str] = None #  String	Optional	Name of the requestor. To view hosts provisioned for multiple requestors, specify a comma-separated list of requestor names (for example, &reqName=symA,symB).
    provName: Optional[str] = None #  String	Optional	Name of the cloud provider (for example, &provName=ibmcloud).
    state: Optional[str] = None #  String	Optional	State of the host provisioned from the cloud. Valid host states are:
    hfcsrftoken: Optional[str] = None #  string	Optional	CSRF token that is obtained with successful login.
    sortBy: Optional[str] = None #  String	Optional	Field name by which data must be sorted, which could be: allocatedTime, hostname, lastFailureInfo, lastFailureTime, launchTime, ncores, ncpus, nram, provName, releaseTime, reqName, returnCount, state, or templateName. While you can sort by all fields, you can specify only one field at a time. For example, to sort by host name, add &sortBy=hostname to the URL. Include the sortOrder parameter to specify the sort order, either ascending or descending.
    sortOrder: Optional[bool] = None #  Boolean	Optional	Order in which to sort data, either ascending (asc) or descending (desc), for the field name specified in the sortBy parameter. For example, to sort host name in ascending order, add &sortBy=hostname&sortOrder=asc.
    pageSize: Optional[int] = None #  Number	Optional	Maximum number of query results per page. You can control this number by configuring the HF_REST_RESULT_DEFAULT_PAGESIZE and HF_REST_RESULT_MAX_PAGESIZE parameters in the hostfactoryconf.json file.
    startIndex: Optional[int] = None #  Number	Optional	Start index of paginated query results. Valid value is 0 (default) or an integer multiple of the pageSize parameter. For example, when pageSize is 25, startIndex must be 0, 25, 50, or so on.

class HFDeleteCloudHosts(RootModel):
    root: List[str]

class HFCloudRequests(BaseModel):
    requestId: Optional[str] = None #	String	Optional	ID of the scale-out request. To view hosts provisioned for multiple request IDs, specify a comma-separated list of request IDs (for example, &requestId=1114,1115).
    requestName: Optional[str] = None #	String	Optional	Name of the scale-out request. To view hosts provisioned with specific request names, specify a comma-separated list of request names (for example, &requestName=LoB1_AppA,LoB1_AppB).
    reqName: Optional[str] = None #	String	Optional	Name of the requestor. To view requests for multiple requestors, specify a comma-separated list of requestor names (for example, reqName=symA,symB).
    provName: Optional[str] = None #	String	Optional	Name of the cloud provider (for example, provName=ibmcloud).
    status: Optional[str] = None #	String	Optional	Status of the host request. Valid request status are:
    submitTime: Optional[str] = None #	String	Optional	The date/time at which the host request was submitted, represented as a number of seconds since Linux® epoch (January 1 1970 00:00:00).
    hfcsrftoken: Optional[str] = None #	string	Optional	CSRF token that is obtained with successful login.
    sortBy: Optional[str] = None #	String	Optional	Field name by which data must be sorted, which could be: ncores, ncpus, ninstance, nram, provName, reqName, status, submitTime, or templateName. While you can sort by all fields, you can specify only one field at a time. For example, to sort by each request's submitted time, add &sortBy=submitTime to the URL. Include the sortOrder parameter to specify the sort order, either ascending or descending.
    sortOrder: Optional[bool] = None #	Boolean	Optional	Order in which to sort data, either ascending (asc) or descending (desc), for the field name specified in the sortBy parameter. For example, to sort submitted time in ascending order, add &sortBy=submitTime&sortOrder=asc.
    pageSize: Optional[int] = None #	Number	Optional	Maximum number of query results per page. You can control this number by configuring the HF_REST_RESULT_DEFAULT_PAGESIZE and HF_REST_RESULT_MAX_PAGESIZE parameters in the hostfactoryconf.json file.
    startIndex: Optional[int] = None #	Number	Optional	Start index of paginated query results. Valid value is 0 (default) or an integer multiple of the pageSize parameter. For example, when pageSize is 25, startIndex must be 0, 25, 50, or so on.

