from types import SimpleNamespace
from google.cloud import compute_v1 as compute
from google.cloud.compute_v1.types import InstancesSetLabelsRequest, SetLabelsInstanceRequest
from gce_provider.config import Config, get_config
from gce_provider.utils.client_factory import instances_client

"""
Sample of instances: 
instances=[
    namespace(
        name='sym-9968d639-a9ac-48b7-ac46-b24782e7b1ab', 
        preservedState=namespace(
            metadatas=[
                namespace(key='symphony_gce_connector', value='AMATKX0F32JN4'),
                namespace(key='symphony-deployment', value='gcp-symphony-hostfactory'),
                namespace(key='symphony-requestId', value='edbbc3a0-d46e-4e4b-a558-2b8398c519d8')
            ]
        )
    ),
    namespace(
        name='sym-191db736-1ef7-45b8-b499-b91d849a1d27',
        preservedState=namespace(
            metadatas=[
                namespace(key='symphony_gce_connector', value='AMATKX0F32JN4'),
                namespace(key='symphony-deployment', value='gcp-symphony-hostfactory'),
                namespace(key='symphony-requestId', value='edbbc3a0-d46e-4e4b-a558-2b8398c519d8')
            ]
        )
    )
]
"""

def set_instance_labels(
    instances: list[SimpleNamespace],
    zone: str,
    config: Config | None
) -> list[str]:
    if config is None:
        config = get_config()

    client = instances_client()

    failed_instances = []    
    for instance in instances:
        try:
            if instance.preservedState.metadatas is not None:
                # get the current label_fingerprint
                current_instance = client.get(
                    project=config.gcp_project_id, zone=zone, instance=instance.name
                )
                label_fingerprint = current_instance.label_fingerprint
                existing_labels = dict(current_instance.labels) if current_instance.labels else {}
                new_labels={
                    metadata.key.lower(): metadata.value.lower()
                    for metadata in instance.preservedState.metadatas
                }
                existing_labels.update(new_labels)
                labels = InstancesSetLabelsRequest(
                    label_fingerprint=label_fingerprint,
                    labels=existing_labels
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