from unittest.mock import patch

import pytest
from kubernetes import config

from gke_provider.k8s import client


def test_load_kubernetes_config_kubeconfig(mock_config):
    """Test loading Kubernetes config from kubeconfig file."""
    with (
        patch("gke_provider.config.Config.__new__", return_value=mock_config),
        patch("kubernetes.config.load_kube_config") as mock_load_kube_config,
    ):
        client.load_kubernetes_config.cache_clear()
        client.load_kubernetes_config()
        mock_load_kube_config.assert_called_once()


def test_load_kubernetes_config_incluster(mock_config):
    """Test loading Kubernetes config from incluster config."""
    with (
        patch(
            "kubernetes.config.load_kube_config", side_effect=config.ConfigException
        ),
        patch("kubernetes.config.load_incluster_config") as mock_load_incluster_config,
    ):
        client.load_kubernetes_config.cache_clear()
        client.load_kubernetes_config()
        mock_load_incluster_config.assert_called_once()


def test_load_kubernetes_config_failure(mock_config):
    """Test loading Kubernetes config failure."""
    with (
        patch.object(
            client, "load_kubernetes_config", side_effect=config.ConfigException
        ),
        patch(
            "kubernetes.config.load_incluster_config",
            side_effect=config.ConfigException,
        ),
        pytest.raises(Exception),
    ):
        client.load_kubernetes_config.cache_clear()
        client.load_kubernetes_config()


def test_get_kubernetes_client():
    """Test getting Kubernetes client."""
    with (
        patch.object(
            client,
            "load_kubernetes_config",
        ),
        patch("kubernetes.client.ApiClient") as MockApiClient,
    ):
        client.get_kubernetes_client()
        MockApiClient.assert_called_once()