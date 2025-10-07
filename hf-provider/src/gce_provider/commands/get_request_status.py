from datetime import timezone
from typing import Optional

from common.model.models import HFRequestStatus, HFRequestStatusResponse
from common.utils.list_utils import flatten
from gce_provider.commands.helpers.request_machine_status_helper import (
    RequestMachineStatusEvaluator,
)
from gce_provider.commands.helpers.request_return_machine_status_helper import (
    RequestReturnMachineStatusEvaluator,
)
from gce_provider.config import Config, get_config
from gce_provider.db.machines import MachineDao
from gce_provider.model.models import HfMachineStatus


def to_machine_response(
    machine: HfMachineStatus,
) -> HFRequestStatusResponse.Request.Machine:
    """Build a machine response object from a machine object"""
    return HFRequestStatusResponse.Request.Machine(
        machineId=machine.machine_name,
        name=machine.machine_name,
        result=machine.hf_machine_result.value,
        status=machine.hf_machine_status.value,
        privateIpAddress=machine.internal_ip,
        publicIpAddress=machine.external_ip,
        launchTime=int(machine.created_at.replace(tzinfo=timezone.utc).timestamp()),
    )


def get_request_status(request: HFRequestStatus, config: Optional[Config] = None):
    if config is None:
        config = get_config()
    config.logger.debug(f"request = {request}")
    # check to see if any element of the request.requests list contains an object with a key "requestId"
    if len(request.requests) < 1 or not any(
        "requestId" in req and req["requestId"] for req in flatten([request.requests])
    ):
        config.logger.error("No requestId found in request")
        raise ValueError("No requestId found.")

    request_list = flatten([request.requests])
    request_responses = []

    for request_item in request_list:
        request_id = request_item["requestId"]
        machines: list[HfMachineStatus] = MachineDao(config).get_machines_for_request(
            request_id
        )

        status_helper = (
            RequestMachineStatusEvaluator
            if (len(machines) > 0 and request_id == machines[0].request_id)
            else RequestReturnMachineStatusEvaluator
        )

        request_status = status_helper.evaluate_request_status(machines)

        machines_response = [to_machine_response(machine) for machine in machines]
        request_responses.append(
            HFRequestStatusResponse.Request(
                requestId=request_id,
                status=request_status.value,
                machines=machines_response,
            )
        )

    result = HFRequestStatusResponse(requests=request_responses)

    return result
