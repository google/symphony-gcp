"""
Unit tests for the utils.py module.
"""

from unittest.mock import AsyncMock, MagicMock, patch

from gcp_symphony_operator.config import Config
from gcp_symphony_operator.utils import (
    check_operator_setup,
    does_namespace_exist,
    does_rbac_exist,
    does_service_account_exist,
    ensure_crd_exists,
)
from kubernetes.client.rest import ApiException
from typing_extensions import Self


class TestDoesNamespaceExist:
    """Tests for the does_namespace_exist function."""

    @patch("gcp_symphony_operator.utils.KubernetesClientManager")
    async def test_namespace_exists(
        self: Self,
        mock_k8s_client_class: MagicMock,
        mock_config: Config,
        mock_logger: MagicMock,
    ) -> None:
        """Test when namespace exists."""
        mock_k8s_client = MagicMock()
        mock_k8s_client_class.return_value = mock_k8s_client

        mock_core_v1 = AsyncMock()
        mock_k8s_client.get_core_v1_api.return_value.__aenter__.return_value = (
            mock_core_v1
        )
        mock_k8s_client._run_in_thread = AsyncMock(
            return_value=AsyncMock()
        )  # Namespace found

        result = await does_namespace_exist(mock_config, mock_logger)

        assert result is True
        mock_k8s_client._run_in_thread.assert_called_once()
        mock_logger.info.assert_called_with("Namespace exists")

    @patch("gcp_symphony_operator.utils.KubernetesClientManager")
    async def test_namespace_does_not_exist(
        self: Self,
        mock_k8s_client_class: MagicMock,
        mock_config: Config,
        mock_logger: MagicMock,
    ) -> None:
        """Test when namespace does not exist."""
        mock_k8s_client = MagicMock()
        mock_k8s_client_class.return_value = mock_k8s_client

        mock_core_v1 = AsyncMock()
        mock_k8s_client.get_core_v1_api.return_value.__aenter__.return_value = (
            mock_core_v1
        )
        mock_k8s_client._run_in_thread = AsyncMock(
            side_effect=[
                ApiException(status=404, reason="Not Found"),
                AsyncMock(),
                AsyncMock(),
            ]
        )

        result = await does_namespace_exist(mock_config, mock_logger)

        assert result is False


class TestDoesRBACExist:
    """Tests for the does_rbac_exist function."""

    @patch("gcp_symphony_operator.utils.KubernetesClientManager")
    async def test_rbac_exists(
        self: Self,
        mock_k8s_client_class: MagicMock,
        mock_config: Config,
        mock_logger: MagicMock,
    ) -> None:
        """Test when RBAC permissions exist."""
        mock_k8s_client = MagicMock()
        mock_k8s_client_class.return_value = mock_k8s_client

        mock_rbac_v1 = AsyncMock()
        mock_k8s_client.get_rbac_v1_api.return_value.__aenter__.return_value = (
            mock_rbac_v1
        )
        mock_k8s_client._run_in_thread = AsyncMock(
            return_value=AsyncMock()
        )  # RBAC found

        result = await does_rbac_exist(mock_config, mock_logger)

        assert result is True
        assert mock_k8s_client._run_in_thread.call_count == 4  # 4 RBAC checks
        mock_logger.info.assert_called_with("RBAC permissions exist")

    @patch("gcp_symphony_operator.utils.KubernetesClientManager")
    async def test_rbac_does_not_exist(
        self: Self,
        mock_k8s_client_class: MagicMock,
        mock_config: Config,
        mock_logger: AsyncMock,
    ) -> None:
        """Test when RBAC permissions do not exist."""
        mock_k8s_client = MagicMock()
        mock_k8s_client_class.return_value = mock_k8s_client

        mock_rbac_v1 = AsyncMock()
        mock_k8s_client.get_rbac_v1_api.return_value.__aenter__.return_value = (
            mock_rbac_v1
        )
        mock_k8s_client._run_in_thread = AsyncMock(
            side_effect=[
                ApiException(status=404, reason="Not Found"),
                AsyncMock(),
                AsyncMock(),
            ]
        )

        result = await does_rbac_exist(mock_config, mock_logger)

        assert result is False


class TestDoesServiceAccountExist:
    """Tests for the does_service_account_exist function."""

    @patch("gcp_symphony_operator.utils.KubernetesClientManager")
    async def test_service_account_exists(
        self: Self,
        mock_k8s_client_class: MagicMock,
        mock_config: Config,
        mock_logger: MagicMock,
    ) -> None:
        """Test when service account exists."""
        mock_k8s_client = MagicMock()
        mock_k8s_client_class.return_value = mock_k8s_client

        mock_core_v1 = AsyncMock()
        mock_k8s_client.get_core_v1_api.return_value.__aenter__.return_value = (
            mock_core_v1
        )
        mock_k8s_client._run_in_thread = AsyncMock(return_value=AsyncMock())

        result = await does_service_account_exist(mock_config, mock_logger)

        assert result is True
        mock_k8s_client._run_in_thread.assert_called_once()
        mock_logger.info.assert_called_with("ServiceAccount exists")

    @patch("gcp_symphony_operator.utils.KubernetesClientManager")
    async def test_service_account_does_not_exist(
        self: Self,
        mock_k8s_client_class: MagicMock,
        mock_config: Config,
        mock_logger: MagicMock,
    ) -> None:
        """Test when service account does not exist."""
        mock_k8s_client = MagicMock()
        mock_k8s_client_class.return_value = mock_k8s_client

        mock_core_v1 = AsyncMock()
        mock_k8s_client.get_core_v1_api.return_value.__aenter__.return_value = (
            mock_core_v1
        )
        mock_k8s_client._run_in_thread = AsyncMock(
            side_effect=[
                ApiException(status=404, reason="Not Found"),
                AsyncMock(),
                AsyncMock(),
            ]
        )

        result = await does_service_account_exist(mock_config, mock_logger)

        assert result is False
        mock_logger.info.assert_called_with("ServiceAccount does not exist")


class TestEnsureCRDExists:
    """Tests for the ensure_crd_exists function."""

    @patch("gcp_symphony_operator.utils.KubernetesClientManager")
    @patch("gcp_symphony_operator.utils.Manifests")
    async def test_crd_exists(
        self: Self,
        mock_manifests_class: MagicMock,
        mock_k8s_client_class: MagicMock,
        mock_config: Config,
        mock_logger: AsyncMock,
    ) -> None:
        """Test when CRD already exists."""
        mock_k8s_client = MagicMock()
        mock_k8s_client_class.return_value = mock_k8s_client

        mock_api_ext_v1 = AsyncMock()
        mock_k8s_client.get_api_ext_v1_api.return_value.__aenter__.return_value = (
            mock_api_ext_v1
        )
        mock_k8s_client._run_in_thread = AsyncMock(return_value=AsyncMock())

        await ensure_crd_exists(mock_config, mock_logger)

        # Should check for both CRDs
        assert mock_k8s_client._run_in_thread.call_count == 2
        mock_manifests_class.assert_not_called()  # No need to create

    @patch("gcp_symphony_operator.utils.KubernetesClientManager")
    @patch("gcp_symphony_operator.utils.Manifests")
    async def test_crd_does_not_exist(
        self: Self,
        mock_manifests_class: MagicMock,
        mock_k8s_client_class: MagicMock,
        mock_config: Config,
        mock_logger: AsyncMock,
    ) -> None:
        """Test when CRD does not exist and needs to be created."""
        mock_k8s_client = MagicMock()
        mock_k8s_client_class.return_value = mock_k8s_client

        mock_api_ext_v1 = AsyncMock()
        mock_ctx_manager = AsyncMock()
        mock_ctx_manager.__aenter__.return_value = mock_api_ext_v1
        mock_k8s_client.get_api_ext_v1_api.return_value = mock_ctx_manager

        # Use a coroutine_like object for each return value
        async def coroutine_like1():
            return MagicMock()

        async def coroutine_like2():
            return MagicMock()

        # Setup _run_in_thread with proper awaitable side effects
        mock_k8s_client._run_in_thread = AsyncMock()
        mock_k8s_client._run_in_thread.side_effect = [
            ApiException(status=404, reason="Not Found"),  # First call raises exception
            coroutine_like1(),  # Second call returns awaitable coroutine
            coroutine_like2(),  # Third call returns awaitable coroutine
        ]

        mock_manifests = MagicMock()
        mock_manifests.crd_manifest.return_value = {"test": "manifest"}
        mock_manifests_class.return_value = mock_manifests

        await ensure_crd_exists(mock_config, mock_logger)

        mock_manifests_class.assert_called_once_with(config=mock_config)
        mock_manifests.crd_manifest.assert_called_once()
        mock_logger.info.assert_any_call(
            "GCPSymphony CRD not found, creating from manifest"
        )


class TestCheckOperatorSetup:
    """Tests for the check_operator_setup function."""

    @patch("gcp_symphony_operator.utils.does_namespace_exist")
    @patch("gcp_symphony_operator.utils.does_service_account_exist")
    @patch("gcp_symphony_operator.utils.does_rbac_exist")
    @patch("gcp_symphony_operator.utils.ensure_crd_exists")
    async def test_check_operator_setup_success(
        self: Self,
        mock_ensure_crd: AsyncMock,
        mock_rbac_exist: AsyncMock,
        mock_sa_exist: AsyncMock,
        mock_ns_exist: AsyncMock,
        mock_config: Config,
        mock_logger: AsyncMock,
    ) -> None:
        """Test successful operator setup check."""
        mock_ns_exist.return_value = True
        mock_sa_exist.return_value = True
        mock_rbac_exist.return_value = True

        await check_operator_setup(mock_config, mock_logger)

        mock_ns_exist.assert_called_once_with(mock_config, mock_logger)
        mock_sa_exist.assert_called_once_with(mock_config, mock_logger)
        mock_rbac_exist.assert_called_once_with(mock_config, mock_logger)
        mock_ensure_crd.assert_called_once_with(mock_config, mock_logger)
