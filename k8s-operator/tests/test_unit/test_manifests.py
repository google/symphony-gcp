import os
from unittest.mock import MagicMock, patch

import pytest
from gcp_symphony_operator.config import Config
from gcp_symphony_operator.manifests import Manifests


@pytest.fixture
def mock_config() -> MagicMock:
    """Fixture for a mock Config object."""
    config = MagicMock(spec=Config)
    config.crd_manifest_path = "manifests/crd"
    config.crd_manifest_file = "crd.yaml"
    config.crd_return_request_manifest_file = "return_request_crd.yaml"
    config.namespace_manifest_path = "manifests/namespace"
    config.namespace_manifest_file = "namespace.yaml"
    config.rbac_manifest_path = "manifests/rbac"
    config.service_account_file = "service_account.yaml"
    config.namespace_role_file = "role.yaml"
    config.cluster_role_file = "cluster_role.yaml"
    config.namespace_role_binding_file = "role_binding.yaml"
    config.cluster_role_binding_file = "cluster_role_binding.yaml"
    config.manifest_base_path = "manifests/operator"
    config.operator_manifest_file = "operator.yaml"
    config.crd_group = "test.group"
    config.crd_api_version = "v1"
    config.crd_kind = "TestResource"
    config.crd_plural = "testresources"
    config.crd_singular = "testresource"
    config.crd_short_name = "tr"
    config.crd_finalizer = "test.group/finalizer"
    config.crd_return_request_kind = "TestReturnRequest"
    config.crd_return_request_plural = "testreturns"
    config.crd_return_request_singular = "testreturn"
    config.crd_return_request_short_name = "trr"
    config.service_account_name = "test-sa"
    config.namespace_role_name = "test-role"
    config.cluster_role_name = "test-cluster-role"
    config.namespace_role_binding_name = "test-role-binding"
    config.cluster_role_binding_name = "test-cluster-role-binding"
    config.operator_name = "test-operator"
    config.operator_image_tag = "latest"
    config.default_container_image = "test-image"
    config.default_container_image_pull_policy = "Always"
    config.log_level = "INFO"
    config.default_namespaces = ["test-ns"]
    config.operator_version = "1.0.0"
    return config


@pytest.fixture
def manifests(mock_config: MagicMock) -> Manifests:
    """Fixture for a Manifests object."""
    with patch("gcp_symphony_operator.manifests.get_config"):
        manifests = Manifests(mock_config)
    return manifests


@patch("gcp_symphony_operator.manifests.Manifests._get_resource_path")
@patch("gcp_symphony_operator.manifests.Manifests._load_and_render_manifest")
def test_manifests_init(
    mock_load_and_render: MagicMock,
    mock_get_resource_path: MagicMock,
    mock_config: Config,
) -> None:
    """Test the Manifests.__init__ method."""
    mock_get_resource_path.return_value = "/path/to/manifests"
    mock_load_and_render.return_value = {"test": "manifest"}

    with patch("gcp_symphony_operator.manifests.get_config"):
        manifests = Manifests(mock_config)

    assert manifests.manifests["namespace"] == {"test": "manifest"}
    assert manifests.manifests["crd"] == {"test": "manifest"}
    assert manifests.manifests["return_request_crd"] == {"test": "manifest"}
    assert manifests.manifests["service_account"] == {"test": "manifest"}
    assert manifests.manifests["role"] == {"test": "manifest"}
    assert manifests.manifests["cluster_role"] == {"test": "manifest"}
    assert manifests.manifests["role_binding"] == {"test": "manifest"}
    assert manifests.manifests["cluster_role_binding"] == {"test": "manifest"}
    assert manifests.manifests["operator"] == {"test": "manifest"}

    assert mock_load_and_render.call_count == 9


@patch("gcp_symphony_operator.manifests.yaml.safe_load")
@patch("jinja2.Environment.get_template")
def test_load_and_render_manifest(
    mock_get_template: MagicMock,
    mock_safe_load: MagicMock,
    manifests: Manifests,
    mock_config: Config,
) -> None:
    """Test the _load_and_render_manifest method."""
    mock_template = MagicMock()
    mock_template.render.return_value = "rendered manifest"
    mock_get_template.return_value = mock_template
    mock_safe_load.return_value = {"test": "data"}

    result = manifests._load_and_render_manifest("test_template.yaml", {"var": "value"})

    mock_get_template.assert_called_once_with("test_template.yaml")
    mock_template.render.assert_called_once_with({"var": "value"})
    mock_safe_load.assert_called_once_with("rendered manifest")
    assert result == {"test": "data"}


@patch("gcp_symphony_operator.manifests.yaml.dump")
@patch("sys.stdout")
def test_export_manifest_stdout(
    mock_stdout: MagicMock,
    mock_yaml_dump: MagicMock,
    manifests: Manifests,
    mock_config: Config,
) -> None:
    """Test the export_manifest method with stdout."""
    manifests.manifests = {"test": {"data": "value"}}
    manifests.__initialized = True
    manifests.export_manifest("-", separate_files=False)

    mock_yaml_dump.assert_called_once()
    mock_stdout.write.assert_called_once_with("---\n")


@patch("gcp_symphony_operator.manifests.yaml.dump")
@patch("builtins.open", new_callable=MagicMock)
def test_export_manifest_separate_files(
    mock_open: MagicMock,
    mock_yaml_dump: MagicMock,
    manifests: Manifests,
    mock_config: Config,
) -> None:
    """Test the export_manifest method with separate files."""
    manifests.manifests = {"test": {"data": "value"}}
    manifests.__initialized = True
    manifests.export_manifest("target_dir", separate_files=True)

    mock_open.assert_called_once_with(os.path.join("target_dir", "test.yaml"), "w")
    mock_yaml_dump.assert_called_once()


def test_crd_manifest(manifests: Manifests, mock_config: Config) -> None:
    """Test the crd_manifest method."""
    manifests.manifests = {"crd": {"test": "crd"}}
    assert manifests.crd_manifest() == {"test": "crd"}


@patch("gcp_symphony_operator.manifests.importlib.resources.files")
def test_get_resource_path(
    mock_resources_files: MagicMock, manifests: Manifests, mock_config: Config
) -> None:
    """Test the _get_resource_path method."""
    mock_resource_location = MagicMock()
    mock_resource_location.__truediv__.return_value = "/path/to/resource"
    mock_resources_files.return_value = mock_resource_location

    result = manifests._get_resource_path("test_resource")

    assert result == str(mock_resource_location.__truediv__.return_value)
    mock_resources_files.assert_called_once()


@patch("gcp_symphony_operator.manifests.get_config")
def test_manifests_singleton(mock_get_config: MagicMock) -> None:
    """Test that Manifests is a singleton."""
    config1 = MagicMock(spec=Config)
    config2 = MagicMock(spec=Config)
    mock_get_config.return_value = config1

    manifests1 = Manifests(config1)
    manifests2 = Manifests(config2)
    assert manifests1 == manifests2
