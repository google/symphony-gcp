from typing import Any, List, Optional

from common.model.models import HFRequest
from gke_provider.config import Config, get_config
from gke_provider.k8s import resources


def get_return_requests(hfr: HFRequest, config: Optional[Config] = None) -> dict[str, Any]:
    """
    Get the status of a machine return request.
    """
    logger = get_config().logger  # logging.getLogger(__name__)
    return_requests = hfr.returnRequests
    if return_requests is None:
        logger.error("returnRequests must be present in the request.")
        return {"message": "returnRequests must be present in the request."}
    logger.info(f"Getting return status for resource: {hfr.returnRequests}")
    if config is None:
        config = get_config()
    machines = return_requests.machines
    if machines is not None and len(machines) == 1 and str(machines[0]).lower() == "all":
        # If the machines field is "ALL", set it to None
        machines = None
    message = ""
    pod_list = None
    if machines:
        if isinstance(machines[0], dict):
            pod_list = [m["name"] for m in machines if "name" in m]  # type: ignore
        elif isinstance(machines[0], str):
            pod_list = machines

    deleted_request_ids: dict = {}
    machines_returned_list: List = []
    try:
        # get the list of machines (pods)
        resource = resources.get_all_gcpsymphonyresources(config.crd_namespace)
        if resource is None:
            return {"message": "There are no return requests in custom provider."}
        else:
            for gcpsr in resource:
                if (
                    "status" in gcpsr
                    and "returnedMachines" in gcpsr["status"]
                    and len(gcpsr["status"]["returnedMachines"]) > 0
                ):
                    if pod_list is not None:
                        for pod in pod_list:
                            dr_id = next(
                                (
                                    p.get("returnRequestId")
                                    for p in gcpsr["status"]["returnedMachines"]
                                    if p.get("name") == pod
                                ),
                                None,
                            )
                            # If we didn't find a returnRequestId, it means the
                            # pod is not in the returnedMachines list
                            if dr_id is not None:
                                if dr_id not in deleted_request_ids.keys():
                                    deleted_request_ids[dr_id] = []
                                deleted_request_ids[dr_id].append(pod)
                                machines_returned_list.append({"gracePeriod": 0, "machine": pod})
                    else:
                        # If pod_list is None, return all returned machines that have
                        # been deleted
                        for deleted_machine in gcpsr["status"]["returnedMachines"]:
                            machines_returned_list.append(
                                {
                                    "gracePeriod": 0,
                                    "machine": deleted_machine.get("name"),
                                }
                            )
            if len(machines_returned_list) > 0:
                message = "Instances marked for termination retrieved successfully."
            return {
                "status": "complete",
                "message": message,
                "requests": machines_returned_list,
            }
    except Exception as e:
        logger.error(f"Error checking GCPSymphonyResource: {e}")
        raise e
