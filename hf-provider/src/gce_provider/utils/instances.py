from types import SimpleNamespace
from typing import Optional
from google.cloud import compute_v1 as compute
from google.cloud.compute_v1.types import (
    InstancesSetLabelsRequest,
    SetLabelsInstanceRequest,
)
from gce_provider.config import Config, get_config
from gce_provider.utils.client_factory import instances_client


def set_instance_labels(
    instances: list[SimpleNamespace], zone: str, config: Optional[Config] = None
) -> list[str]:
    """
    set_instance_labels

    Take any key value pairs in an instance's preservedState.metadatas object and apply them
    as labels on said instance.

    args:
        instances: A list of instance objects to update
        zone: The zone in which the instances are located
        config: Optional configuration object

    returns: A list of instance names that failed to update
    """
    if config is None:
        config = get_config()

    client = instances_client()
    failed_instances = []

    # Batch fetch all instances to avoid N+1 queries
    instance_map = {}
    instance_names = [inst.name for inst in instances if inst.preservedState.metadatas]

    for name in instance_names:
        try:
            instance_map[name] = client.get(
                project=config.gcp_project_id, zone=zone, instance=name
            )
        except Exception as e:
            config.logger.error(f"Error fetching instance {name}: {e}")
            failed_instances.append(name)

    for instance in instances:
        try:
            if instance.preservedState.metadatas is None:
                continue

            current_instance = instance_map.get(instance.name)
            if not current_instance:
                continue

            existing_labels = (
                dict(current_instance.labels) if current_instance.labels else {}
            )
            new_labels = {
                metadata.key.lower(): metadata.value.lower()
                for metadata in instance.preservedState.metadatas
            }
            existing_labels.update(new_labels)

            labels = InstancesSetLabelsRequest(
                label_fingerprint=current_instance.label_fingerprint,
                labels=existing_labels,
            )
            request = SetLabelsInstanceRequest(
                project=config.gcp_project_id,
                zone=zone,
                instance=instance.name,
                instances_set_labels_request_resource=labels,
            )
            client.set_labels(request=request)
        except Exception as e:
            config.logger.error(f"Error setting instance labels: {e}")
            failed_instances.append(instance.name)

    return failed_instances
