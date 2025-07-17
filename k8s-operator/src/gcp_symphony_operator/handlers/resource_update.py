import datetime
from logging import Logger
from typing import Any, Dict

import kopf
from gcp_symphony_operator.config import Config
from gcp_symphony_operator.k8s.core_v1 import call_list_namespaced_pod
from gcp_symphony_operator.k8s.custom_objects import (
    call_patch_namespaced_custom_object_status,
)
from gcp_symphony_operator.profiling import log_execution_time
from kubernetes.client import ApiException, V1PodList


def resource_update_handler_factory(config: Config, logger: Logger) -> Any:
    """Factory function for creating the resource update handler."""

    @log_execution_time(logger)
    @kopf.on.field(  # type: ignore
        config.crd_group,
        config.crd_api_version,
        config.crd_plural,
        field="status.availableMachines",
    )  # type: ignore
    async def update_gcpsymphonyresource_when_no_machines(
        new: int,
        old: int | None,
        spec: Dict[str, Any] | None,
        meta: Dict[str, Any],
        status: Dict[str, Any] | None,
        logger: Logger,
        **kwargs: Any | None,
    ) -> None:
        """Handle GCPSymphonyResource updates when availableMachines becomes 0."""
        if old is None or old < 1 or new is None or new > 0:
            return

        resource_name = meta["name"]
        namespace = meta["namespace"]
        request_id = meta.get("labels", {}).get("symphony.requestId")

        try:
            # Check for existing pods
            pod_selector = f"symphony.requestId={request_id}"
            logger.debug(f"calling list_namespaced_pod with selector: {pod_selector}")
            pod_list = await call_list_namespaced_pod(
                namespace=namespace,
                label_selector=pod_selector,
            )
            if not isinstance(pod_list, V1PodList):
                raise TypeError(
                    f"Expected V1PodList, got {type(pod_list)} for resource {resource_name}"
                )
            logger.debug(
                f"list_namespaced_pod returned {len(pod_list.items or [])} items"
            )
            # Filter out pods marked for deletion
            active_pods = [
                pod
                for pod in (pod_list.items or [])
                if pod.metadata.deletion_timestamp is None
            ]
            pod_list.items = active_pods

            if not pod_list.items:
                logger.debug(
                    f"{config.crd_kind} {resource_name} has no pods, marking as completed."
                )
                existing_conditions = status.get("conditions", []) if status else []
                filtered_conditions = [
                    c for c in existing_conditions if c.get("type") != "Completed"
                ]
                new_condition = {
                    "type": "Completed",
                    "status": "True",
                    "reason": "NoPods",
                    "message": f"{config.crd_kind} {resource_name} has no pods.",
                    "lastTransitionTime": (
                        datetime.datetime.now(datetime.timezone.utc).isoformat()
                    ),
                }
                updated_conditions = filtered_conditions + [new_condition]
                patch_body = {"status": {"conditions": updated_conditions}}
                await call_patch_namespaced_custom_object_status(
                    namespace=namespace, name=resource_name, patch_body=patch_body
                )
            else:
                logger.error(
                    f"{config.crd_kind} {resource_name} still has pods, not deleting."
                )

        except ApiException as e:
            if e.status == 404:
                logger.warning(
                    f"{config.crd_kind} {resource_name} not found, but continuing with update."
                )
            else:
                logger.error(f"Error deleteing {config.crd_kind} {resource_name}: {e}")

    return update_gcpsymphonyresource_when_no_machines
