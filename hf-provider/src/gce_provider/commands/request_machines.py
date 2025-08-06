from typing import Optional

import google.cloud.compute_v1 as compute

from common.model.models import HFRequestMachinesResponse
from gce_provider.config import Config, get_config
from gce_provider.db.machines import MachineDao
from gce_provider.model.models import HFGceRequestMachines
from gce_provider.utils import client_factory
from gce_provider.utils.string_utils import generate_unique_id


def request_machines(
    hfr: HFGceRequestMachines, config: Optional[Config] = None
) -> HFRequestMachinesResponse:
    """
    Request machines to be provisioned.
    """
    if config is None:
        config = get_config()
    logger = config.logger

    logger.debug(f"hf_request = {hfr}")

    if hfr and hfr.template:
        count = hfr.template.machineCount
    else:
        # Handle the case where requestMachines, or template is missing
        logger.error(f"HFRequest is invalid: {hfr}")
        raise ValueError("Invalid request format")

    instance_prefix = config.gcp_instance_prefix
    request_id = generate_unique_id()

    logger.info(f"Received request to provision {count} machines with prefix {instance_prefix}")

    # Prepare labels for the instances
    labels = {
       "symphony-deployment": f"{config.hf_provider_name}-hostfactory",
       "symphony-requestId": request_id,
       config.instance_label_name_text: config.instance_label_value_text
    }

    instances = [
        compute.PerInstanceConfig(
            name=f"{instance_prefix}{generate_unique_id()}",
            preserved_state=compute.PreservedState(
                metadata=labels
            )
        )
        for _ in range(count)
    ]

    try:
        client = client_factory.instance_group_managers_client()
        request = compute.CreateInstancesInstanceGroupManagerRequest(
            project=config.gcp_project_id,
            request_id=request_id,
            zone=hfr.gcp_zone,
            instance_group_manager=hfr.gcp_instance_group,
            instance_group_managers_create_instances_request_resource=compute.InstanceGroupManagersCreateInstancesRequest(  # noqa: E501
                instances=instances,
            ),
        )
        result = client.create_instances(request=request)
        logger.debug(f"Submitted request {request_id}")

        MachineDao(config).store_request_machines(result.name, request)
        return HFRequestMachinesResponse(requestId=request_id)
    except Exception as e:
        logger.error(f"Error creating GCPSymphonyResource: {e}")
        raise e
