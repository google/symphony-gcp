import re
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Sequence

import google.cloud.compute_v1 as compute
from tenacity import retry, wait_exponential

from gce_provider.model.models import InstanceIps, ResourceIdentifier
from gce_provider.utils import client_factory


def fetch_managed_instance_list(
    project: str, zone: str, instance_group: str
) -> Sequence[compute.Instance]:
    """List instances in an instance group"""
    client = client_factory.instance_group_managers_client()

    request = compute.ListManagedInstancesInstanceGroupManagersRequest(
        project=project,
        zone=zone,
        instance_group_manager=instance_group,
    )
    response = client.list_managed_instances(request=request)
    return [instance.instance for instance in response]  # returns full URI of instances


@retry(wait=wait_exponential(multiplier=1, min=4, max=60))
def fetch_instance(ident: ResourceIdentifier) -> Optional[compute.Instance]:
    """Given instance identifiers, get the info about the instance"""
    client = client_factory.instances_client()
    return client.get(
        project=ident.project,
        zone=ident.zone,
        instance=ident.name,
    )


def parse_resource_url(instance_url: str) -> Optional[ResourceIdentifier]:
    """Convert an instance URL, to a structured object"""
    match = re.match(
        r".*projects/(?P<project>[^/]+)/zones/(?P<zone>[^/]+)/(?P<type>[^/]+)/(?P<name>[^/]+)",
        instance_url,
    )
    if not match:
        return None

    return ResourceIdentifier(
        project=match.group("project"),
        zone=match.group("zone"),
        name=match.group("name"),
        resourceType=match.group("type"),
    )


def to_resource_url(project: str, zone: str, name: str, resource_type: str = "instances") -> str:
    """Generate a partial GCP URL for a given resource"""
    return f"/compute/v1/projects/{project}/zones/{zone}/{resource_type}/{name}"


def fetch_instance_by_url(instance_url: str) -> Optional[compute.Instance]:
    """Given an instance URL, get the info about the instance"""
    return fetch_instance(parse_resource_url(instance_url))


def fetch_instances(
    instances: Sequence[ResourceIdentifier],
) -> Sequence[compute.Instance]:
    """Simultaneously get multiple instances"""
    with ThreadPoolExecutor(max_workers=10) as executor:
        return list(executor.map(fetch_instance, instances))


def fetch_instances_by_url(instance_urls) -> Sequence[compute.Instance]:
    """Simultaneously get multiple instances"""
    with ThreadPoolExecutor(max_workers=10) as executor:
        return list(executor.map(fetch_instance_by_url, instance_urls))


def extract_instance_ips(instance: compute.Instance) -> InstanceIps:
    # Get the primary internal and external IP
    network_interface = instance.network_interfaces[0]
    internal_ip = network_interface.network_i_p
    external_ip = (
        network_interface.access_configs[0].nat_ip if network_interface.access_configs else None
    )

    return InstanceIps(
        name=instance.name,
        internal_ip=internal_ip,
        external_ip=external_ip,
    )
