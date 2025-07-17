from typing import Any, Dict, Optional

import yaml

from common.model.models import HFRequest
from gke_provider.config import Config, get_config
from gke_provider.k8s import resources, utils


def request_machines(hfr: HFRequest, config: Optional[Config] = None) -> Dict[str, Any]:
    """
    Request machines (pods) to be provisioned.
    """
    if config is None:
        config = get_config()
    logger = config.logger

    logger.debug(f"hf_request = {hfr}")

    # count = 0
    # pod_spec = None

    if hfr and hfr.requestMachines and hfr.requestMachines.template and hfr.pod_spec:
        count = hfr.requestMachines.template.machineCount
        pod_spec = hfr.pod_spec
    else:
        # Handle the case where requestMachines, template, or pod_spec is missing
        logger.error(f"HFRequest is invalid: {hfr}")
        raise ValueError("Invalid request format")

    logger.info(f"pod_spec:\n---{yaml.dump(pod_spec)}")

    name_prefix = utils.generate_unique_id()

    # amazonq-ignore-next-line
    logger.info(f"Received request to provision {count} machines with prefix {name_prefix}")

    labels = {
        "symphony.deployment": "hf-service",
        "symphony.requestId": name_prefix,
    }

    try:
        # Create the GCPSymphonyResource
        resource = resources.create_gcpsymphonyresource(
            name_prefix=name_prefix,
            count=count,
            pod_spec=pod_spec,
            namespace=config.crd_namespace,
            group=config.crd_group,
            kind=config.crd_kind,
            version=config.crd_version,
            labels=labels,
        )

        logger.info(f"###### resource: {resource}")

        return {
            "message": (
                f"Request submitted for {count} machines with name "
                f"{resource['metadata']['name']}"
            ),
            "requestId": name_prefix,
        }
    except Exception as e:
        logger.error(f"Error creating GCPSymphonyResource: {e}")
        raise e
