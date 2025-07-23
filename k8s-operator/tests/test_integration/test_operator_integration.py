"""
Integration tests for the k8s-operator.
"""

import time
from typing import Any, Generator, Literal
from unittest.mock import patch

import kubernetes.client as k8s
import pytest
from gcp_symphony_operator.config import Config
from kubernetes.client.rest import ApiException
from typing_extensions import Self


@pytest.mark.integration
class TestOperatorIntegration:
    """Integration tests for the operator."""

    @pytest.fixture
    def test_namespace(
        self: Self,
    ) -> Generator[Any, None]:
        """Create a test namespace for integration tests."""
        namespace_name = "test-symphony-operator"
        api = k8s.CoreV1Api()

        # Create namespace if it doesn't exist
        try:
            api.read_namespace(name=namespace_name)
        except ApiException as e:
            if e.status == 404:
                namespace = k8s.V1Namespace(
                    metadata=k8s.V1ObjectMeta(name=namespace_name)
                )
                api.create_namespace(body=namespace)
                # Wait for namespace to be active
                time.sleep(2)

        yield namespace_name

        # Cleanup - delete namespace
        try:
            api.delete_namespace(name=namespace_name)
        except ApiException:
            pass

    @pytest.fixture
    def test_config(
        self: Self, test_namespace: Literal["test-symphony-operator"]
    ) -> Generator[Config, Any, None]:
        """Create a test configuration."""
        with patch.object(Config, "_instance", None):
            with patch.dict(
                "os.environ",
                {
                    "GCP_HF_DEFAULT_NAMESPACES": test_namespace,
                    "GCP_HF_LOG_LEVEL": "DEBUG",
                    "GCP_HF_KUBERNETES_RBAC_CHECK": "false",
                },
            ):
                config = Config()
                yield config

    @pytest.mark.skip(reason="Requires a running Kubernetes cluster")
    def test_namespace_exists(
        self: Self,
        test_config: Config,
        test_namespace: Literal["test-symphony-operator"],
    ) -> None:
        """Test that the namespace exists."""
        from gcp_symphony_operator.utils import does_namespace_exist

        assert does_namespace_exist(test_config, test_config.logger) is True

    @pytest.mark.skip(reason="Requires a running Kubernetes cluster")
    def test_create_service_account(
        self: Self,
        test_config: Config,
        test_namespace: Literal["test-symphony-operator"],
    ) -> None:
        """Test creating a service account."""
        from gcp_symphony_operator.manifests import Manifests

        manifests = Manifests()
        sa_manifest = manifests.crd_manifest().get("service_account")

        api = k8s.CoreV1Api()
        try:
            api.create_namespaced_service_account(
                namespace=test_namespace, body=sa_manifest
            )

            # Verify service account was created
            sa = api.read_namespaced_service_account(
                name=test_config.service_account_name, namespace=test_namespace
            )
            assert sa is not None
            assert isinstance(sa, k8s.V1ServiceAccount)
            assert (
                sa.metadata is not None
                and sa.metadata.name == test_config.service_account_name
            )

        except ApiException as e:
            pytest.fail(f"Failed to create service account: {e}")
        finally:
            # Cleanup
            try:
                api.delete_namespaced_service_account(
                    name=test_config.service_account_name, namespace=test_namespace
                )
            except ApiException:
                pass
