from functools import wraps
from logging import INFO as loggingINFO
from logging import WARNING as loggingWARNING
from logging import Logger

from gcp_symphony_operator.config import Config
from gcp_symphony_operator.k8s.clients import KubernetesClientManager
from gcp_symphony_operator.manifests import Manifests
from kubernetes.client.rest import ApiException
from tenacity import retry, stop_after_attempt, wait_exponential


async def does_namespace_exist(config: Config, logger: Logger) -> bool:
    """
    Ensures the operator's namespace exists in the target cluster.
    """
    k8s_client = KubernetesClientManager(config)
    async with k8s_client.get_core_v1_api() as core_v1:
        try:
            _ = await k8s_client._run_in_thread(
                core_v1.read_namespace, name=config.default_namespaces[0]
            )
            logger.info("Namespace exists")
            return True
        except ApiException as e:
            if e.status == 404:
                logger.info(f"Namespace '{config.default_namespaces[0]} does not exist")
                return False
            else:
                logger.error(f"API Error checking Namespace: {e}")
                raise


async def does_rbac_exist(config: Config, logger: Logger) -> bool:
    """
    Ensures the necessary RBAC permissions exist for the operator.
    Returns True or False
    """
    k8s_client = KubernetesClientManager(config)

    async with k8s_client.get_rbac_v1_api() as rbac_v1:
        try:
            await k8s_client._run_in_thread(
                rbac_v1.read_cluster_role, name=config.cluster_role_name
            )
            await k8s_client._run_in_thread(
                rbac_v1.read_cluster_role_binding, name=config.cluster_role_binding_name
            )  # type: ignore
            await k8s_client._run_in_thread(
                rbac_v1.read_namespaced_role,
                name=config.namespace_role_name,
                namespace=config.default_namespaces[0],
            )  # type: ignore
            await k8s_client._run_in_thread(
                rbac_v1.read_namespaced_role_binding,
                name=config.namespace_role_binding_name,
                namespace=config.default_namespaces[0],
            )  # type: ignore
            logger.info("RBAC permissions exist")
            return True
        except ApiException as e:
            if e.status == 404:
                logger.info("One or moreRBAC permissions do not exist")
                return False
            elif e.status == 403:
                logger.info(
                    f"Service account does not have correct permissions.\n{e.body}"
                )
                return False
            else:
                logger.error(f"API Error checking RBAC permissions: {e}")
                raise


async def does_service_account_exist(config: Config, logger: Logger) -> bool:
    """
    Ensures the operator's ServiceAccount exists in the target namespace.
    Creates it if it doesn't exist.
    """
    k8s_client = KubernetesClientManager(config)

    async with k8s_client.get_core_v1_api() as core_v1:
        try:
            await k8s_client._run_in_thread(
                core_v1.read_namespaced_service_account,
                name=config.service_account_name,
                namespace=config.default_namespaces[0],
            )  # type: ignore
            logger.info("ServiceAccount exists")
            return True
        except ApiException as e:
            if e.status == 404:
                logger.info("ServiceAccount does not exist")
                return False
            elif e.status == 403:
                logger.info("ServiceAccount does not have correct permissions.")
                return False
            else:
                logger.error(f"API Error checking ServiceAccount: {e}")
                raise


async def ensure_crd_exists(config: Config, logger: Logger) -> None:
    """
    Ensures the GCPSymphony CRD exists in the cluster.
    If not, deploys it from the manifest file.
    """
    k8s_client = KubernetesClientManager(config)

    async with k8s_client.get_api_ext_v1_api() as api_ext_v1:
        try:
            await k8s_client._run_in_thread(
                api_ext_v1.read_custom_resource_definition,
                name=f"{config.crd_plural}.{config.crd_group}",
            )
        except ApiException as e:
            if e.status == 404:
                logger.info("GCPSymphony CRD not found, creating from manifest")
                manifests = Manifests(config=config)
                crd_manifest = manifests.crd_manifest()
                try:
                    await k8s_client._run_in_thread(
                        api_ext_v1.create_custom_resource_definition, body=crd_manifest
                    )
                    logger.info("Successfully created GCPSymphony CRD")
                except Exception as create_error:
                    logger.error(f"Failed to create CRD: {create_error}")
                    raise
            else:
                logger.error(f"Error checking CRD: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error checking/creating CRD: {e}")
            raise
        try:
            await k8s_client._run_in_thread(
                api_ext_v1.read_custom_resource_definition,
                name=f"{config.crd_return_request_plural}.{config.crd_group}",
            )
        except ApiException as e:
            if e.status == 404:
                logger.error(
                    "MachineReturnRequest CRD is not found, creating from manifest"
                )
                manifests = Manifests(config=config)
                mrr_manifest = manifests.return_request_manifest()
                logger.debug(f"MachineReturnRequest CRD manifest:\n{mrr_manifest}\n")
                try:
                    await k8s_client._run_in_thread(
                        api_ext_v1.create_custom_resource_definition, body=mrr_manifest
                    )
                    logger.info("Successfully created MachineReturnRequest CRD")
                except Exception as create_error:
                    logger.error(
                        f"Failed to create MachineReturnRequest CRD: {create_error}"
                    )
                    raise
            else:
                logger.error(f"Error checking CRD readiness: {e}")
                raise
        except Exception as e:
            logger.error(
                f"Unexpected error checking/creating MachineReturnRequest CRD: {e}"
            )
            raise


async def check_operator_setup(config: Config, logger: Logger) -> None:
    """
    Ensures all necessary resources exist for the operator to function.
    Order matters here:
    1. ServiceAccount (needed for RBAC)
    2. RBAC (needed for CRD operations)
    3. CRD (needed for operator function)
    """

    try:
        # check if the namespace exists
        if not await does_namespace_exist(config, logger):
            raise RuntimeError(
                f"Namespace '{config.default_namespaces[0]}' "
                "does not exist. Please create it before proceeding."
            )

        # Check for ServiceAccount and RBAC permissions
        if not await does_service_account_exist(
            config, logger
        ) or not await does_rbac_exist(config, logger):
            raise RuntimeError(
                "The ServiceAccount or RBAC permissions do not exist. "
                "Please create them before proceeding."
                "\nTp export the RBAC manifests, from the src direcotory utilize the command\n\n"
                "\t'python -m gcp_symphony_operator.main export-manifests'\n\n"
            )

        # Ensure CRD exists
        await ensure_crd_exists(config, logger)

    except Exception as e:
        logger.error(f"Failed to complete operator setup: {e}")
        raise


def retry_with_lazy_config(get_config_fn):
    """A version of retry that gets retry parameters at runtime"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            config = get_config_fn()
            retry_decorator = retry(
                stop=stop_after_attempt(config.crd_update_retry_count),
                wait=wait_exponential(
                    multiplier=1, min=config.crd_update_retry_interval, max=10
                ),
                before_sleep=_before_sleep,
                reraise=True,
            )
            return await retry_decorator(func)(*args, **kwargs)

        def _before_sleep(retry_state):
            logger = get_config_fn().logger
            if retry_state.attempt_number < 1:
                loglevel = loggingINFO
            else:
                loglevel = loggingWARNING
            logger.log(
                loglevel,
                "Retrying %s: attempt %s ended with: %s",
                retry_state.fn.__name__,
                retry_state.attempt_number,
                retry_state.outcome.exception() or "success",
            )

        return wrapper

    return decorator
