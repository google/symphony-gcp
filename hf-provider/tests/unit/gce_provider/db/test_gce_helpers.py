from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest

from gce_provider.db.gce_helpers import (
    fetch_managed_instance_list,
    fetch_instance,
    fetch_instance_by_url,
    fetch_instances,
    fetch_instances_by_url,
    extract_instance_ips,
    parse_resource_url,
)
from gce_provider.model.models import ResourceIdentifier
from tests.unit.gce_provider.fixtures import mock_config

TEST_PROJECT = "symphony-dev-1"
TEST_ZONE = "us-central-1"


@pytest.fixture
def mock_managed_instance():
    """Create mock managed instance responses"""

    def _create_fixture(url: str):
        return MagicMock(instance=url)

    return _create_fixture


@patch("gce_provider.db.gce_helpers.client_factory.instance_group_managers_client")
def test_list_managed_instances(mock_client, mock_managed_instance, mock_config):
    mock_instances = [
        mock_managed_instance(
            generate_instance_url(
                project=TEST_PROJECT, zone=TEST_ZONE, name=f"my-instance-{i}"
            )
        )
        for i in range(2)
    ]

    mock_client.list_managed_instances.return_value = mock_instances

    result = fetch_managed_instance_list(
        "symphony-dev-1", "us-central1-c", "corykim-test-01"
    )
    assert mock_instances[0].instance in result
    assert mock_instances[1].instance in result
    mock_client.list_managed_instances.assert_called_once()


@pytest.fixture
def mock_instance():
    def _create(name: str, internal_ip: str, external_ip: str = None):
        access_configs = []
        if external_ip:
            access_configs = [SimpleNamespace(nat_ip=external_ip)]

        network_interface = SimpleNamespace(
            network_i_p=internal_ip,
            access_configs=access_configs,
        )

        return SimpleNamespace(
            name=name,
            network_interfaces=[network_interface],
        )

    return _create


@patch("gce_provider.db.gce_helpers.client_factory.instances_client")
def test_fetch_instance(mock_client, mock_instance):
    # Setup mock return value
    instance_name = "my-instance-1"
    mock_client.get.return_value = mock_instance(
        instance_name, "10.0.0.100", "35.100.200.1"
    )

    # Call the function under test
    instance = fetch_instance(
        ResourceIdentifier(project=TEST_PROJECT, zone=TEST_ZONE, name=instance_name)
    )

    # Validate
    assert instance.name == instance_name
    assert instance.network_interfaces[0].network_i_p == "10.0.0.100"
    assert instance.network_interfaces[0].access_configs[0].nat_ip == "35.100.200.1"
    mock_client.get.assert_called_once()


@patch("gce_provider.db.gce_helpers.client_factory.instances_client")
def test_fetch_instance_by_url(mock_client, mock_instance):
    # Setup mock return value
    instance_name = "my-instance-1"
    mock_client.get.return_value = mock_instance(
        instance_name, "10.0.0.100", "35.100.200.1"
    )

    # Call the function under test
    instance = fetch_instance_by_url(generate_instance_url(instance_name))

    # Validate
    assert instance.name == instance_name
    assert instance.network_interfaces[0].network_i_p == "10.0.0.100"
    assert instance.network_interfaces[0].access_configs[0].nat_ip == "35.100.200.1"
    mock_client.get.assert_called_once()


def generate_instance_url(
    name: str, zone: str = TEST_ZONE, project: str = TEST_PROJECT
):
    return f"https://www.googleapis.com/compute/v1/projects/{project}/zones/{zone}/instances/{name}"


@patch("gce_provider.db.gce_helpers.client_factory.instances_client")
def test_fetch_instances(mock_client, mock_instance):
    # Setup mock return value
    instance_names = [f"multi-instance-{i + 1}" for i in range(2)]

    mock_instances = [
        mock_instance(name, f"10.0.0.{i + 1}", f"35.100.200.{i + 1}")
        for i, name in enumerate(instance_names)
    ]

    mock_client.get.side_effect = mock_instances

    instance_args = [
        ResourceIdentifier(project=TEST_PROJECT, zone=TEST_ZONE, name=name)
        for name in instance_names
    ]

    # Call the function under test
    instances = fetch_instances(instance_args)

    # Validate
    assert len(instances) == len(instance_names)
    assert mock_client.get.call_count == len(instance_names)

    for instance in instances:
        assert instance is not None
        assert instance.name in instance_names


@patch("gce_provider.db.gce_helpers.client_factory.instances_client")
def test_fetch_many_instances(mock_client, mock_instance):
    # Setup mock return value
    instance_names = [f"multi-instance-{i + 1}" for i in range(1000)]

    mock_instances = [
        mock_instance(name, f"10.0.0.{i + 1}", f"35.100.200.{i + 1}")
        for i, name in enumerate(instance_names)
    ]

    mock_client.get.side_effect = mock_instances

    instance_args = [
        ResourceIdentifier(project=TEST_PROJECT, zone=TEST_ZONE, name=name)
        for name in instance_names
    ]

    # Call the function under test
    instances = fetch_instances(instance_args)

    # Validate
    assert len(instances) == len(instance_names)
    assert mock_client.get.call_count == len(instance_names)

    for instance in instances:
        assert instance is not None
        assert instance.name in instance_names


@patch("gce_provider.db.gce_helpers.client_factory.instances_client")
def test_fetch_instances_by_url(mock_client, mock_instance):
    # Setup mock return value
    instance_names = [f"multi-instance-{i + 1}" for i in range(2)]
    mock_instances = [
        mock_instance(name, f"10.0.0.{i + 1}", f"35.100.200.{i + 1}")
        for i, name in enumerate(instance_names)
    ]

    mock_client.get.side_effect = mock_instances

    # Call the function under test
    instances = fetch_instances_by_url(
        [generate_instance_url(name) for name in instance_names]
    )

    # Validate
    assert len(instances) == len(instance_names)
    assert mock_client.get.call_count == len(instance_names)

    for instance in instances:
        assert instance is not None
        assert instance.name in instance_names


def test_extract_instance_ips(mock_instance):
    instance = mock_instance("my-instance", "10.0.0.1", "35.100.200.1")
    result = extract_instance_ips(instance)
    assert result.name == instance.name
    assert result.internal_ip == instance.network_interfaces[0].network_i_p
    assert result.external_ip == instance.network_interfaces[0].access_configs[0].nat_ip


def test_parse_url():
    url = generate_instance_url("my-instance")
    result = parse_resource_url(url)
    assert result.name == "my-instance"
    assert result.project == TEST_PROJECT
    assert result.zone == TEST_ZONE
    assert result.resourceType == "instances"
