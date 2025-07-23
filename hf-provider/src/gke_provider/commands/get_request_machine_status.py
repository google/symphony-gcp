import datetime
from datetime import timezone
from typing import Any, Optional

from common.model.models import HFRequest
from common.utils.profiling import log_execution_time
from gke_provider.config import Config, get_config
from gke_provider.k8s import resources

STATUS_COMPLETE = "complete"
STATUS_COMPLETE_WITH_ERROR = "complete_with_error"
STATUS_RUNNING = "running"


@log_execution_time(resources.get_logger())
def get_request_machine_status(
    hfr: HFRequest, config: Optional[Config] = None
) -> Optional[dict[str, Any]]:
    """
    Get the status of a machine request.
    """
    if config is None:
        config = get_config()
    logger = config.logger

    single_request = False
    if not hfr.requestStatus:
        raise ValueError("Invalid request format: Missing requestStatus")
    if hfr.requestStatus.requests is not None:
        # IBM documentation doesn't clarify if the request is a list of requestIds or a single one.
        # Handle either option. Use a flag to determine whether to return a list or single object.
        single_request, requests = _get_request_list(hfr)
        request_ids = []
        # get the list of requestIDs into a single list for iteration
        for id in requests:
            if "requestId" in id:
                request_ids.append(id["requestId"])
        if request_ids is None or len(request_ids) < 1:
            raise ValueError("Invalid request format: Missing requestId in requests")
    else:
        raise ValueError("Invalid request format: Missing requests in requestStatus")

    logger.info(f"Received a getRequestMachineStatus for requestIds: {request_ids}")

    return_list = []
    request = {}
    for id in request_ids:
        # build a single requestStatus return object to add to the return_list.
        try:
            request = None
            # Get the GCPSymphonyResource
            resource = resources.get_resource_status(requestId=id, namespace=config.crd_namespace)
            if type(resource) is not dict:
                raise ValueError(f"Error getting deployment and pod data for requestId: {id}")
            if resource.get("kind") == config.crd_kind:
                request = _process_gcpsr(resource, id)
            elif resource.get("kind") == config.crd_return_request_kind:
                request = _process_mrr(resource, id)
            elif resource.get("kind") is None:
                # Handle situations where the resource is not found
                request = _process_for_no_resource(resource, id)
            if len(request) > 0 if request is not None else False:
                return_list.append(request)
        except Exception as e:
            logger.error(f"Error getting custom resource: {e}")
            raise e

    return {"requests": return_list} if not single_request else {"requests": request}


POD_RESULT_EXECUTING = "executing"
POD_RESULT_SUCCEED = "succeed"
POD_RESULT_FAIL = "fail"

POD_STATUS_RUNNING = "running"
POD_STATUS_STOPPED = "stopped"
POD_STATUS_TERMINATED = "terminated"


@log_execution_time(resources.get_logger())
def _process_gcpsr(resource: dict, id: str) -> dict[str, Any]:
    is_any_pod_status_failed = False
    is_any_pod_result_executing = False

    pod_list = []
    if "pods" in resource and len(resource["pods"]) > 0:
        for pod in resource["pods"]:
            pod_details = _extract_pod_details(pod)
            pod_list.append(pod_details)
            is_any_pod_status_failed = (
                is_any_pod_status_failed or pod_details["status"] == POD_STATUS_TERMINATED
            )
            is_any_pod_result_executing = is_any_pod_result_executing or pod_details["result"] == (
                "%s" % POD_RESULT_EXECUTING
            )

    message = ""
    if "phase" in resource and "error" in resource["phase"]:
        status = STATUS_COMPLETE_WITH_ERROR
        message = f"Error getting information for requestId: {id}"
    elif is_any_pod_result_executing:
        status = STATUS_RUNNING
        message = "Some machines are still being deployed."
    elif is_any_pod_status_failed:
        status = STATUS_COMPLETE_WITH_ERROR
        message = "Some machines have failed."
    else:
        status = STATUS_COMPLETE
    return {
        "requestId": id,
        "message": message,
        "status": status,
        "machines": pod_list,
    }


@log_execution_time(resources.get_logger())
def datetime_to_utc_int(dt: datetime.datetime) -> int:
    """Converts a datetime object to a timestamp, in UTC timezone."""
    if dt.tzinfo is None:
        dt_utc = dt.replace(tzinfo=timezone.utc)
    else:
        dt_utc = dt.astimezone(timezone.utc)
    return int(dt_utc.timestamp())


@log_execution_time(resources.get_logger())
def _extract_pod_details(pod: dict[str, Any]) -> dict[str, Any]:
    pod_status, pod_result = _map_pod_results(pod)
    launch_time = pod.get("status", {}).get("start_time")
    launch_time_int = datetime_to_utc_int(launch_time) if launch_time else ""
    return {
        "machineId": pod.get("metadata", {}).get("uid", "unknown"),
        "name": pod.get("metadata", {}).get("name", "uknown"),
        "result": pod_result,  # 'executing', 'fail', 'succeed'
        "status": pod_status,
        "privateIpAddress": pod.get("status", {}).get("pod_ip", "unknown"),
        "publicIpAddress": "",
        "launchtime": launch_time_int,
        "message": f"Deployed in namespace: {pod.get('metadata', {}).get('namespace', 'unknown')}",
    }


def _get_request_list(hfr: HFRequest) -> tuple[bool, list]:
    """
    Determine if the request is a single request or a list of requests.
    """
    single_request = False

    if hfr.requestStatus is None:
        raise ValueError("Invalid request format: Missing requestStatus")

    requests_attr = getattr(hfr.requestStatus, "requests", None)

    if requests_attr is None:
        raise ValueError("Invalid request format: Missing requests in requestStatus")

    if isinstance(requests_attr, dict):
        requests = [requests_attr]
        single_request = True
    elif isinstance(requests_attr, list):
        requests = requests_attr
    else:
        raise ValueError(
            "Invalid request format: requestStatus.requests "
            "should include a single dict or list of dicts"
        )

    return single_request, requests


def _map_pod_results(pod: Optional[dict[str, Any]]) -> tuple[str, str]:
    """
    Map the pod results to the expected values.
    """
    if pod is None:
        return "unknown", "unknown"

    # translates k8s pod details to Symphony's requests.machines.result
    #   "result": "(mandatory)(string) "Status of this request related to this machine.
    #       Possible values:  'executing', 'fail', 'succeed'.
    #       For example, call requestMachines with templateId and machineCount 3,
    #       and then call getRequestStatus to check the status of this request. We
    #       should get 3 machines with result 'succeed'. If any machine is missing
    #       or the status is not correct, that machine is not usable.",
    pod_result_map = {
        "pending": POD_RESULT_EXECUTING,
        "running": POD_RESULT_SUCCEED,
        "succeeded": POD_RESULT_SUCCEED,
        "failed": POD_RESULT_FAIL,
        "unknown": POD_RESULT_FAIL,
    }

    # translates k8s pod details to Symphony's requests.machines.status
    #   "status" : "(optional)(string) Status of machine.
    #   Expected values: running, stopped, terminated, shutting-down, stopping."
    pod_status_map = {
        "pending": POD_STATUS_RUNNING,
        "running": POD_STATUS_RUNNING,
        "succeeded": POD_STATUS_STOPPED,
        "failed": POD_STATUS_TERMINATED,
        "unknown": POD_STATUS_TERMINATED,
    }
    # TODO: capture all pod condition edge cases.
    pod_phase = pod["status"]["phase"].lower()

    pod_result = pod_result_map.get(pod_phase, POD_RESULT_FAIL)
    pod_status = pod_status_map.get(pod_phase, POD_STATUS_TERMINATED)

    return pod_status, pod_result


def _process_mrr(resource: dict, id: str) -> dict[str, Any]:
    return_request_map = {
        "Completed": STATUS_COMPLETE,
        "InProgress": STATUS_RUNNING,
        "PartiallyCompleted": STATUS_COMPLETE_WITH_ERROR,
        "Failed": STATUS_COMPLETE_WITH_ERROR,
    }
    status = return_request_map.get(resource.get("phase", ""), STATUS_COMPLETE_WITH_ERROR)
    message = None
    if status == STATUS_COMPLETE_WITH_ERROR:
        message = (
            f"{resource.get('status', {}).get('failedMachines', 0)} "
            "machines failed to return properly."
        )
    return {
        "requestId": id,
        "status": status,
        "message": message or "<No message>",
        "machines": [],
    }


def _process_for_no_resource(resource: dict, id: str) -> dict[str, Any]:
    """
    Process the case where no resource is found for the request ID.
    This is a fallback for when the resource is not found.
    This can happen if the custom resource was deleted through the cleanup worker
    or never created.
    """
    return {
        "requestId": id,
        "status": STATUS_COMPLETE_WITH_ERROR,
        "message": f"No resource found for requestId: {id}",
        "machines": [],
    }
