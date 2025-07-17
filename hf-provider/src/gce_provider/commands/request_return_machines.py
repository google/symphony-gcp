from typing import Optional

import google.cloud.compute_v1 as compute

from common.model.models import HFRequestReturnMachines, HFRequestReturnMachinesResponse
from common.utils.list_utils import flatten
from gce_provider.config import Config, get_config
from gce_provider.db.gce_helpers import to_resource_url
from gce_provider.db.machines import MachineDao
from gce_provider.model.models import HfMachine
from gce_provider.utils import client_factory
from gce_provider.utils.string_utils import generate_unique_id


def request_return_machines(hfr: HFRequestReturnMachines, config: Optional[Config] = None):
    """Request machines to be deleted"""
    if config is None:
        config = get_config()
    logger = config.logger

    logger.debug(f"hf_request = {hfr}")
    request_id = generate_unique_id()

    db_machines = MachineDao(config)

    machine_names = [machine.name for machine in flatten([hfr.machines])]
    machine_data = db_machines.get_machines_by_name(machine_names)

    # group the machines into instance groups and zones
    machines: dict[str, dict[str, list[HfMachine]]] = {}
    for machine in machine_data:
        if machine.instance_group_manager in machines:
            instance_group = machines[machine.instance_group_manager]
            if machine.gcp_zone in instance_group:
                instance_group[machine.gcp_zone].append(machine)
            else:
                instance_group[machine.gcp_zone] = [machine]
        else:
            machines[machine.instance_group_manager] = {machine.gcp_zone: [machine]}

    client = client_factory.instance_group_managers_client()
    for instance_group in machines:
        for zone in machines[instance_group]:
            # batch the deletions
            batch_size = 1000
            try:
                for i in range(0, len(machines[instance_group][zone]), batch_size):
                    batch = machines[instance_group][zone][i : i + batch_size]
                    instance_urls = [
                        to_resource_url(
                            project=config.gcp_project_id,
                            zone=zone,
                            name=machine.machine_name,
                        )
                        for machine in batch
                    ]
                    request = compute.DeleteInstancesInstanceGroupManagerRequest(
                        request_id=generate_unique_id(),
                        project=config.gcp_project_id,
                        zone=zone,
                        instance_group_manager=instance_group,
                        instance_group_managers_delete_instances_request_resource=compute.InstanceGroupManagersDeleteInstancesRequest(  # noqa: E501
                            instances=instance_urls,
                            skip_instances_on_validation_error=True,
                        ),
                    )
                    result = client.delete_instances(request=request)
                    logger.debug(f"Submitted request {request_id}")

                    MachineDao(config).store_delete_machines(request_id, result.name, request)
            except Exception as e:
                logger.error(f"Error returning machines: {e}")
                raise e

    return HFRequestReturnMachinesResponse(requestId=request_id)
