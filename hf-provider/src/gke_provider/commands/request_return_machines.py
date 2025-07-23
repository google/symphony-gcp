from typing import Any, Dict, Union

from common.model.models import HFRequest
from gke_provider.config import get_config
from gke_provider.k8s import resources
from gke_provider.k8s.utils import generate_unique_id


def request_return_machines(hfr: HFRequest) -> Dict[str, Any]:
    """
    Request machines (pods) to be returned.

    * The output of this function is a JSON object with the following structure:
    {
    "message": "(optional)(string) Any additional message the caller should know",
    "requestId": "(mandatory)(string) Unique ID to identify this request in the cloud provider"
    }
    """
    config = get_config()
    logger = config.logger  # logging.getLogger(__name__)
    logger.debug(f"Request to return machines for resource(s): {hfr}")

    ################################################
    # Internal functions
    ################################################
    def _get_machine_list(hfr: HFRequest) -> tuple[bool, Union[list, dict]]:
        """
        Determine if the request is a single request or a list of requests.
        """
        single_request = False
        if (
            hasattr(hfr, "requestReturnMachines") is False
            or hfr.requestReturnMachines is None
        ):
            raise ValueError("Invalid request format: Missing requestReturnMachines")

        if type(hfr.requestReturnMachines.machines) is dict:
            single_request = True
        elif type(hfr.requestReturnMachines.machines) is not list:
            raise ValueError(
                "Invalid request format: requests should include a single or list of objects"
            )

        return single_request, (
            [hfr.requestReturnMachines.machines]
            if single_request
            else hfr.requestReturnMachines.machines
        )

    ################################################
    # Main function
    ################################################
    logger.debug(f"Request to return machines for resource(s): {hfr}")

    request_id = generate_unique_id()
    if not hfr.requestReturnMachines:
        raise ValueError("Invalid request format")
    if hfr.requestReturnMachines.machines is not None:
        # IBM documentation doesn't clarify if the machines is a list of names or a single one.
        # Handle either option. Use a flag to determine whether to return a list or single object.
        single_request, machines = _get_machine_list(hfr)
        hostnames = []
        # get the list of hostnames into a single list for iteration
        for host in machines:
            if hasattr(host, "name") and host.name:
                hostnames.append(host.name)
        if hostnames is None or len(hostnames) < 1:
            raise ValueError("Invalid request format: Missing name in machines")
    else:
        raise ValueError(
            "Invalid request format: Missing machines in requestReturnMachines"
        )

    logger.info(f"Received a requestReturnMachines for machines: {hostnames}")

    try:
        result = resources.create_machine_return_request_resource(
            request_id=request_id, machine_ids=hostnames, namespace=config.crd_namespace
        )
    except Exception as e:
        logger.error(f"Error creating {config.crd_return_request_kind} resource: {e}")
        raise

    msg = "Success"
    resourceVersion = result["metadata"].get("resourceVersion", None)

    if resourceVersion is None:
        msg = (
            f"Failed to create {config.crd_return_request_kind} resource, "
            "returned resourceVersion is None"
        )
        logger.error(msg)

    return {"message": msg, "requestId": request_id}
