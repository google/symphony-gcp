import asyncio
import datetime
from typing import Any, Dict

from gcp_symphony_operator.config import Config
from gcp_symphony_operator.k8s.custom_objects import (
    call_delete_namespaced_custom_object,
    call_list_namespaced_custom_object,
)
from kubernetes.client import ApiException


class CleanupWorker:
    """Thread-safe cleanup worker with its own Kubernetes clients."""

    def __init__(self, config: Config):
        self.config = config
        self.logger = config.logger
        self.stop_event = asyncio.Event()
        self.task: asyncio.Task | None = None

        # Ensure config is initialized
        if not getattr(config, "_Config__initialized", False):
            raise RuntimeError(
                "Config object not properly initialized. Use await get_config() first."
            )

    async def start(self) -> None:
        """Start the cleanup worker."""
        if self.task is None or self.task.done():
            self.logger.info(
                f"Starting cleanup worker with interval of "
                f"{self.config.crd_completed_check_interval} minutes."
            )
            self.task = asyncio.create_task(self._cleanup_loop())
            # Add callback to handle exceptions
            self.task.add_done_callback(self._task_done_callback)
        else:
            self.logger.warning("Cleanup worker is already running.")
        self.logger.info("✅ Cleanup worker started")

    async def stop(self) -> None:
        """Stop the cleanup worker."""
        self.logger.info("🛑 Stopping cleanup worker...")
        self.stop_event.set()
        if self.task:
            await self.task
            self.logger.info("✅ Cleanup worker stopped")

    def _task_done_callback(self, task) -> None:
        """Callback for when the cleanup task is done."""
        try:
            task.result()
        except asyncio.CancelledError:
            self.logger.info("Cleanup worker task was cancelled.")
        except Exception as e:
            self.logger.error(f"Exception in cleanup worker task: {e}")
            self.logger.exception(e)

    async def _cleanup_loop(self) -> None:
        """Main cleanup loop."""
        while not self.stop_event.is_set():
            self.config.logger.info("Starting cleanup cycle")
            try:
                for plural in self.config.crd_plural_map.values():
                    await self._cleanup_resources(plural)

                self.config.logger.info(
                    "Cleanup cycle completed. Sleeping for "
                    f"{self.config.crd_completed_check_interval} minutes."
                )
                # Sleep for configured crd_completed_check_interval minutes
                await asyncio.sleep(self.config.crd_completed_check_interval * 60)

            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)  # Wait before retry

    async def _cleanup_resources(self, plural) -> None:
        """Clean up expired resources."""
        plural = plural or self.config.crd_plural
        try:
            # Get resources waiting for cleanup
            resources = await call_list_namespaced_custom_object(
                namespace=self.config.default_namespaces[0],
                label_selector=f"symphony.waitingCleanup={str(True)}",
                plural=plural,
            )
            # iterate over the list of resources awaiting cleanup
            # and call the appropriate function
            for resource in resources.get("items", []):
                if plural == self.config.crd_plural:
                    await self._process_gcpsr(resource)
                elif plural == self.config.crd_return_request_plural:
                    await self._process_mrr(resource)

        except ApiException as e:
            self.logger.error(f"Error listing resources for cleanup: {e}")

    async def _process_gcpsr(self, resource: Dict[str, Any]) -> None:
        """Process individual resource for cleanup."""
        resource_name = resource.get("metadata", {}).get("name")
        if not resource_name:
            return

        # Look for the condition with type="Completed" and status="True"
        # use the "lastTransitionTime" to determine if it has expired
        conditions = resource.get("status", {}).get("conditions", [])
        pod_deleted_condition = next(
            (c for c in conditions if c.get("type") == "Completed"), {}
        )

        if pod_deleted_condition.get("status") == "True":
            deleted_time_str = pod_deleted_condition.get("lastTransitionTime")
            if deleted_time_str and self._is_expired(deleted_time_str):
                self.logger.debug(f"Deleting {resource['kind']} {resource_name}")
                try:
                    await self._delete_resource(resource)
                    self.logger.debug(f"Deleted {resource['kind']}: {resource_name}")
                except ApiException as e:
                    self.logger.error(
                        "Error deleting " f"{resource['kind']}  {resource_name}: {e}"
                    )

    async def _process_mrr(self, resource: Dict[str, Any]) -> None:
        """Process MachineReturnRequest resource for cleanup."""
        resource_name = resource.get("metadata", {}).get("name")
        if not resource_name:
            return

        status = resource.get("status", {}).get("phase", "")
        if status in ["Completed", "Failed"]:
            # get the lastTransitionTime from the AllPodsDeleted condition
            conditions: list = resource.get("status", {}).get("conditions", [])
            apd_condition: dict[str, Any] = next(
                (
                    condition
                    for condition in conditions
                    if (
                        condition.get("type") == "AllPodsDeleted"
                        and condition.get("status") == "True"
                    )
                ),
                {},
            )
            # check to see if the lastTransitionTime is set
            # and if it has expired based on the configured retain time
            if apd_condition["lastTransitionTime"]:
                last_transition_time_str = apd_condition["lastTransitionTime"]
                if last_transition_time_str and self._is_expired(
                    last_transition_time_str
                ):
                    self.logger.debug(f"Deleting {resource['kind']} {resource_name}")
                    # Delete the resource
                    try:
                        await self._delete_resource(resource)
                        self.logger.debug(
                            f"Deleted {resource['kind']}: {resource_name}"
                        )
                    except ApiException as e:
                        self.logger.error(
                            f"Error deleting {resource['kind']} "
                            f"{resource_name}: {e}"
                        )

    def _is_expired(self, time_str: str) -> bool:
        """Check if custom resource has expired based on
        the lastTransitionTime and the configured retain time."""
        try:
            deleted_time = datetime.datetime.fromisoformat(
                time_str.replace("Z", "+00:00")
            )
            retain_time = datetime.timedelta(
                minutes=self.config.crd_completed_retain_time
            )
            return (
                datetime.datetime.now(datetime.timezone.utc) - deleted_time
                > retain_time
            )
        except ValueError:
            return False

    async def _delete_resource(self, resource: Dict[str, Any]) -> None:
        """Delete a custom resource."""
        resource_name = resource["metadata"]["name"]
        try:
            await call_delete_namespaced_custom_object(
                name=resource_name,
                namespace=resource["metadata"]["namespace"],
                plural=self.config.crd_plural_map[resource["kind"]],
            )
            self.logger.info("Deleted expired " f"{resource['kind']}: {resource_name}")
        except ApiException as e:
            if e.status == 404:
                self.logger.info(f"{resource['kind']}: {resource_name} already deleted")
            else:
                self.logger.error(
                    f"Failed to delete {resource['kind']}: {resource_name}: {e}"
                )
        except Exception as e:
            self.logger.error(
                f"Unexpected error deleting {resource['kind']}: "
                f"{resource_name}: {e}"
            )
