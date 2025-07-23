import datetime
from logging import Logger
from typing import Any, Dict, List, Optional

import kopf
from gcp_symphony_operator.api.v1.types.gcp_symphony_resource import (
    Condition,
    GCPSymphonyResource,
)
from gcp_symphony_operator.config import Config
from gcp_symphony_operator.k8s.custom_objects import call_get_custom_object
from gcp_symphony_operator.workers.status_update import (
    UpdateEvent,
    enqueue_status_update,
)
from kubernetes.client import ApiException


def container_state_handler_factory(config: Config, logger: Logger) -> Any:
    """
    Factory function to create a pod phase handler.
    This function creates a handler for pod phase changes and updates the custom
    resource status accordingly.
    """

    @kopf.on.field(  # type: ignore # noqa
        "v1",
        "pod",
        field="status.containerStatuses",
        when=(
            lambda meta, **_: meta.get("labels", {}).get(  # type: ignore
                "managed-by", ""
            )
            == config.operator_name
        ),
    )
    async def pod_container_status_handler(
        meta: Dict[str, Any],
        spec: Optional[Dict[str, Any]],
        status: Optional[Dict[str, Any]],
        old: Optional[List[Dict]],
        new: Optional[List[Dict]],
        logger: Logger,
        **kwargs: Any,
    ) -> None:  # type: ignore  # noqa
        """
        Handle container status changes for pods managed by this operator.
        Updates the custom resource status based on container status changes.

        Container states:
        - waiting: Container is waiting to start
        - running: Container is currently runningkubec
        - terminated: Container has terminated (with success or failure)
        """
        logger.debug(
            f"Starting pod_container_status_handler for pod {meta.get('name', 'Unknown')} "
            f"old={old}, new={new}"
        )

        try:
            pod_name: str = meta.get("name", "Unknown")
            namespace: str = (
                meta.get("namespace", "Unknown") or config.default_namespaces[0]
            )

            # Early validation
            request_id = meta.get("labels", {}).get("symphony.requestId", None)
            if not request_id:
                logger.error(f"Pod {pod_name} has no requestId label")
                return

            # Skip if no container statuses
            if not new:
                logger.debug(f"Pod {pod_name} has no new container status")
                return

            # Validate owner references
            owner_references = meta.get("ownerReferences", [])
            if not owner_references:
                logger.error(f"Pod {pod_name} has no owner references")
                return

            # Find the GCPSymphonyResource owner using list comprehension
            cr_owner = next(
                (
                    owner
                    for owner in owner_references
                    if owner.get("kind", "") == config.crd_kind
                    and owner.get("apiVersion", "")
                    == f"{config.crd_group}/{config.crd_api_version}"
                ),
                None,
            )
            if not cr_owner:
                logger.error(f"Pod {pod_name} not owned by a {config.crd_kind}")
                return

            # Process container status changes
            container_changes = []
            for container_status in new:
                container_name = container_status.get("name", "")

                # Find the old status for this container
                old_container_status = next(
                    (
                        (c for c in old if c.get("name", "") == container_name)
                        if old
                        else iter([])
                    ),
                    None,
                )

                current_state = container_status.get("state")
                previous_state = (
                    old_container_status.get("state", "")
                    if old_container_status
                    else None
                )
                # Skip if no state change
                if current_state == previous_state and previous_state is not None:
                    continue

                logger.debug(
                    f"Container {container_name} in pod {pod_name} "
                    f"state changed from {previous_state or 'Unknown'} "
                    f"to {current_state or 'Unknown'}"
                )

                container_changes.append(
                    {
                        "name": container_name,
                        "previous_state": previous_state,
                        "current_state": current_state,
                        "details": (
                            c.to_str()
                            for c in (container_status.get("state") or {})
                            if c is not None
                        ),
                    }
                )

            if not container_changes:
                logger.debug(f"No container state changes detected for pod {pod_name}")
                return

            # Get and validate custom resource
            try:
                cr_dict = await call_get_custom_object(
                    name=cr_owner.get("name", "unknown"),  # type: ignore
                    namespace=namespace,
                    plural=config.crd_plural,
                )  # type: ignore
                cr = GCPSymphonyResource(**cr_dict) if cr_dict else None  # type: ignore
            except ApiException as e:
                if e.status == 404:
                    logger.error(
                        f"{config.crd_kind} {cr_owner.get('name', 'unknown')} not found, "
                        "skipping container status update"
                    )
                    return
                else:
                    logger.error(
                        f"Error fetching {config.crd_kind} {cr_owner.get('name', 'unknown')}: {e}, "
                        "skipping container status update"
                    )
                    raise

            if not isinstance(cr, GCPSymphonyResource):
                logger.error(
                    f"{config.crd_kind} {cr_owner.get('name', 'unknown')} is invalid or not found, "
                    "skipping container status update"
                )
                return

            # Create container health condition
            all_containers_ready = all(
                container_status.get("ready", False) for container_status in new
            )

            new_condition = Condition(
                type="ContainerHealth",
                status="True" if all_containers_ready else "False",
                lastTransitionTime=datetime.datetime.now(
                    datetime.timezone.utc
                ).isoformat(),
                reason=(
                    "ContainersReady" if all_containers_ready else "ContainersNotReady"
                ),
                message=(
                    f"All containers in pod {pod_name} are ready"
                    if all_containers_ready
                    else f"Not all containers in pod {pod_name} are ready"
                ),
            )

            logger.debug(
                f"Calling enqueue_status_update for pod {pod_name} container status updates..."
            )

            update_event: UpdateEvent = UpdateEvent(
                cr_name=cr.metadata.get("name", "unknown"),
                namespace=namespace,
                new_condition=new_condition,
                pod_name=pod_name,
                pod_status=status or {},
                request_id=request_id,
            )
            # Enqueue the status update
            await enqueue_status_update(update_event=update_event)

            logger.info(
                f"Enqueued container status update for pod {pod_name} in "
                f"{config.crd_kind} {cr_owner.get('name', 'unknown')}"
            )

        except Exception as e:
            logger.error(f"Unexpected error in pod container status handler: {e}")
            logger.exception(e)

    return pod_container_status_handler
