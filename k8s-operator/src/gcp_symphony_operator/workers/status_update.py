import asyncio
import asyncio.queues as aio_queue
import enum
from functools import lru_cache
from logging import Logger
from typing import Any, Dict, List, Optional

from gcp_symphony_operator.api.v1.types.gcp_symphony_resource import (
    Condition,
    ReturnedMachine,
)
from gcp_symphony_operator.config import Config, get_config
from gcp_symphony_operator.k8s.core_v1 import call_list_namespaced_pod
from gcp_symphony_operator.k8s.custom_objects import (
    call_get_custom_object,
    call_patch_namespaced_custom_object,
    call_patch_namespaced_custom_object_status,
)
from gcp_symphony_operator.profiling import log_execution_time
from gcp_symphony_operator.workers.context import get_op_context
from kubernetes.client import ApiException, V1Pod
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential
from typing_extensions import Self


@lru_cache(maxsize=1)
def _get_config() -> Config:
    """Get the configuration object."""
    try:
        config = asyncio.get_event_loop().run_until_complete(get_config(thin=True))
        return config
    except Exception as e:
        raise RuntimeError(
            f"Failed to get configuration. Ensure Config is initialized properly.\n{e}"
        )


class ResourcePhase(str, enum.Enum):
    WAITING_CLEANUP = "WaitingCleanup"
    RUNNING = "Running"
    PENDING = "Pending"
    DEGRADED = "Degraded"
    UNKNOWN = "Unknown"


class PodPhase(str, enum.Enum):
    FAILED = "Failed"
    NOT_READY = "NotReady"
    PENDING = "Pending"
    RUNNING = "Running"
    SUCCEEDED = "Succeeded"
    TERMINATING = "Terminating"
    UNKNOWN = "Unknown"


class PodConditionType(str, enum.Enum):
    READY = "Ready"
    DISRUPTED = "DisruptionTarget"
    COMPLETED = "Completed"
    FAILED = "Failed"
    TERMINATING = "Terminating"
    RETURNED = "PodReturned"


class UpdateEvent(BaseModel):
    """
    Represents an update event for GCPSymphonyResource.
    This is used to enqueue updates for processing by the worker.
    """

    cr_name: str
    namespace: str
    new_condition: Optional[Condition] = None
    pod_name: Optional[str] = None
    pod_status: Optional[dict] = None
    returned_machines: Optional[List[ReturnedMachine]] = None
    request_id: str = ""


class StatusUpdateWorker:
    """
    A worker thread that processes GCPSymphonyResource status updates from a queue.
    """

    def __init__(
        self, config: Config,
        update_queue: aio_queue.Queue,
        stop_event: asyncio.Event,
        status_check: bool = False
    ) -> None:
        self.config = config
        self.update_queue = update_queue
        self.stop_event = stop_event
        self.worker_task: asyncio.Task | None = None
        self.status_check: bool = status_check

    async def start(self: Self) -> None:
        """
        Starts the worker thread.
        """
        try:
            if self.worker_task is None or self.worker_task.done():
                self.config.logger.debug("Initializing StatusUpdateWorker...")
                self.config.logger.info("🔄 Creating status update worker task")
                # Initialize reusable clients
                # await self._init_clients()
                self.worker_task = asyncio.create_task(self.update_resource_loop())
                # Add a done callback to handle exceptions
                self.worker_task.add_done_callback(self._task_done_callback)
        except Exception as e:
            self.config.logger.error("❌ Error starting StatusUpdateWorker")
            self.config.logger.exception(f"Stack trace: {e}")
            raise
        self.config.logger.info("✅ StatusUpdateWorker start completed")

    def _task_done_callback(self: Self, task: asyncio.Task) -> None:
        """
        Callback for when the worker task is done.
        This will log any exceptions raised during the task execution.
        """
        try:
            task.result()  # This will raise any exceptions from the task
        except asyncio.CancelledError:
            self.config.logger.info("✅ StatusUpdateWorker task was cancelled.")
        except Exception as e:
            self.config.logger.error("❌ Exception in worker task.")
            self.config.logger.exception(f"Stack trace: {e}")

    async def update_resource_loop(self: Self) -> None:
        """
        Main loop for the worker thread.
        """
        if self.status_check:
            self.config.logger.info(
                "Performing initial status check for existing pods..."
            )
            # Enqueue initial status checks for existing pods
            # This could be implemented as needed
            self.status_check = await self._get_current_status()  # Reset after first run
        while not self.stop_event.is_set():
            try:
                # Collect multiple updates in a batch
                updates = await self._collect_batch_updates()
                if updates:
                    await self._process_batch_updates(updates)
            except Exception as e:
                self.config.logger.error(f"Error processing batch updates: {e}")
                self.config.logger.exception(e)
            await asyncio.sleep(1)  # Sleep to avoid busy waiting

    async def _collect_batch_updates(self) -> list[UpdateEvent]:
        """Collect multiple updates from queue for batch processing."""
        updates = []
        batch_size = self.config.crd_update_batch_size

        try:
            # Get first update with timeout
            first_update_dict = await asyncio.wait_for(
                self.update_queue.get(), timeout=2
            )
            first_update = UpdateEvent(**first_update_dict)
            updates.append(first_update)

            # Log queue size for debugging
            queue_size = self.update_queue.qsize()
            self.config.logger.debug(f"Queue size after first get: {queue_size}")

            # Collect additional updates without blocking
            for i in range(batch_size - 1):
                try:
                    update_dict = self.update_queue.get_nowait()
                    update = UpdateEvent(**update_dict)
                    updates.append(update)
                except asyncio.QueueEmpty:
                    self.config.logger.debug(
                        f"Queue empty after collecting {i} additional items"
                    )
                    break

        except asyncio.TimeoutError:
            # No updates available, return empty list
            pass

        return updates

    async def _process_batch_updates(self, updates: list[UpdateEvent]) -> None:
        """
        Process multiple updates, grouping by resource for efficiency.
        """
        # Group updates by resource using defaultdict for cleaner code
        from collections import defaultdict

        resource_groups = defaultdict(list)
        for update in updates:
            key = (update.namespace, update.cr_name)
            resource_groups[key].append(update)

        # Process each resource group
        for (namespace, cr_name), resource_updates in resource_groups.items():
            try:
                await self._process_resource_updates(
                    namespace, cr_name, resource_updates
                )
            except Exception as e:
                self.config.logger.error(f"Error processing updates for {cr_name}: {e}")
            finally:
                # Mark all updates as done
                for _ in resource_updates:
                    self.update_queue.task_done()

    async def _process_resource_updates(
        self, namespace: str, cr_name: str, updates: list[UpdateEvent]
    ) -> None:
        """
        Filter through a resource's batch of updates and process all that have a
        condition of type "Completed" and the latest update for any other
        condition type.
        """
        from itertools import groupby

        # separate out any "Completed" conditioins in an UpdateEvent
        completed_updates = [
            u
            for u in updates
            if u.new_condition and u.new_condition.type == "Completed"
        ]
        # For non-completed updates, keep only latest per pod
        other_updates = [
            u
            for u in updates
            if not (u.new_condition and u.new_condition.type == "Completed")
        ]
        # sort, group and keep only the latest update per pod
        latest_other_updates = [
            max(group, key=lambda u: getattr(u, "timestamp", 0))
            for pod_name, group in groupby(
                sorted(other_updates, key=lambda u: u.pod_name or ""),
                key=lambda u: u.pod_name,
            )
        ]
        # Combine completed updates with latest non-completed updates
        final_updates = completed_updates + latest_other_updates
        # Process all updates for this resource in a single batch
        try:
            await self._process_consolidated_updates(namespace, cr_name, final_updates)
        except ApiException as e:
            if e.status == 409:
                self.config.logger.error(
                    f"Conflict updating {self.config.crd_kind} {cr_name}: {e}"
                )
            elif e.status == 404:
                self.config.logger.error(f"{self.config.crd_kind} {cr_name} not found")
                return
            else:
                raise
        except Exception as e:
            self.config.logger.error(f"Error processing updates for {cr_name}: {e}")
            raise

    @log_execution_time(_get_config().logger)  # type: ignore
    @retry(
        stop=stop_after_attempt(_get_config().crd_update_retry_count),
        wait=wait_exponential(
            multiplier=1,
            min=_get_config().crd_update_retry_interval,
            max=5,
        ),
        reraise=True,
    )
    async def _process_consolidated_updates(
        self, namespace: str, cr_name: str, updates: list[UpdateEvent]
    ) -> None:
        """
        Process all batched updates for a single resource.
        """

        # Get current resource state once
        cr: Dict = await call_get_custom_object(
            name=cr_name, namespace=namespace, plural=self.config.crd_plural
        )  # type: ignore

        if not cr:
            self.config.logger.error(
                f"{self.config.crd_kind} {cr_name} not found in namespace {namespace}"
            )
            return

        # Extract and validate resource data
        metadata = cr.get("metadata", {})
        resource_version = metadata.get("resourceVersion", "")
        cr_request_id = metadata.get("labels", {}).get("symphony.requestId", "")

        if not resource_version:
            self.config.logger.error(
                f"{self.config.crd_kind} {cr_name} has no resourceVersion"
            )
            # It's not possible to patch a custom resource without a resourceVersion
            return

        # Get current status components
        conditions = cr.get("status", {}).get("conditions", [])
        returned_machines = (
            cr.get("status", {}).get("returnedMachines", []).copy()
            if cr.get("status", {}).get("returnedMachines", [])
            else []
        )

        # Apply all updates
        updated_conditions = self._merge_conditions(conditions, updates)
        returned_machines = self._apply_machine_updates(returned_machines, updates)

        # Get phase once for all updates
        cr_phase, available_machines = await get_gcpsymphonyresource_phase(
            request_id=cr_request_id,
            namespace=namespace,
            logger=self.config.logger,
            config=self.config,
        )

        # Update resource status
        await self._update_resource_status(
            namespace,
            cr_name,
            resource_version,
            cr_phase,
            updated_conditions,
            available_machines,
            returned_machines,
        )

        # Handle cleanup label if needed
        if cr_phase == ResourcePhase.WAITING_CLEANUP:
            await self._patch_cleanup_label(namespace, cr_name)

        self.config.logger.info(
            f"Updated {self.config.crd_kind} {cr_name} with {len(updates)} "
            f"updates, phase: {cr_phase}"
        )
        return  # Success

    def _merge_conditions(
        self, existing_conditions: list[dict], updates: list[UpdateEvent]
    ) -> list[dict]:
        """
        Merge conditions from existing and new updates, and ensure we keep
        only latest of each type.
        """
        condition_map = {c.get("type"): c for c in existing_conditions}

        for update in updates:
            new_condition = update.new_condition
            if new_condition and (condition_type := new_condition.type):
                condition_map[condition_type] = new_condition.model_dump()

        # We only want the list of conditions, not the map
        return list(condition_map.values())

    @log_execution_time(_get_config().logger)  # type: ignore
    def _apply_machine_updates(
        self, returned_machines: List[dict], updates: list[UpdateEvent]
    ) -> List[dict]:
        """
        Take all the updates provided and ensure that they end up
        on the returnedMachines list.
        """
        for update in updates:
            pod_name = update.pod_name
            pod_status = update.pod_status or {}
            returned_hostnames = [
                p.get("name") for p in returned_machines if p.get("name")
            ]

            if (not pod_name or not pod_status) and pod_name in returned_hostnames:
                continue

            # Handle machine state transitions
            # add a pod to the returnedMachines list[dict] if it is in a terminal state
            existing_machine = next(
                (rm for rm in returned_machines if rm.get("name") == pod_name),
                None,
            )
            if not existing_machine:
                # Theoretically, the PodReturned should be the last condition
                # that we put on the pod, so it should always make it this far
                # and not get sorted out by the earlier grouping-sorting logic
                if (
                    update.new_condition
                    and update.new_condition.type == "PodReturned"
                    and update.new_condition.status == "True"
                ):
                    # set the values for adding the ReturnedMachine to the list
                    returned_pod = next(
                        (
                            rp
                            for rp in update.returned_machines or []
                            if rp.name == update.pod_name
                        ),
                        None,
                    )
                    if returned_pod:
                        returned_machines.append(returned_pod.dict())
        return returned_machines

    @log_execution_time(_get_config().logger)  # type: ignore
    async def _update_resource_status(
        self,
        namespace: str,
        cr_name: str,
        resource_version: str,
        phase: str,
        conditions: list,
        available_machines: int,
        returned_machines: List[dict],
    ) -> None:
        """Update the resource status."""
        updated_resource = {
            "status": {
                "conditions": conditions,
                "phase": phase,
                "availableMachines": available_machines,
                "returnedMachines": returned_machines,
            },
        }

        try:
            await call_patch_namespaced_custom_object_status(
                name=cr_name, namespace=namespace, patch_body=updated_resource
            )
        except Exception as e:
            self.config.logger.error(
                f"Error updating {self.config.crd_kind} {cr_name} status: {e}"
            )

    async def _patch_cleanup_label(self, namespace: str, cr_name: str) -> None:
        """Patch cleanup label for WaitingCleanup phase."""
        patch_body = {"metadata": {"labels": {"symphony.waitingCleanup": str(True)}}}
        try:
            await call_patch_namespaced_custom_object(
                name=cr_name, namespace=namespace, patch_body=patch_body
            )
        except ApiException as e:
            if e.status not in [409, 404]:
                self.config.logger.error(
                    f"Error patching cleanup label for {cr_name}: {e}"
                )

    async def stop(self: Self) -> None:
        """
        Shuts down the status update queue and worker thread.
        """
        self.config.logger.info("🛑 Stopping StatusUpdateWorker task.")
        self.stop_event.set()

        if self.worker_task and not self.worker_task.done():
            try:
                await self.worker_task
            except asyncio.CancelledError:
                self.config.logger.debug("Status update worker task was cancelled")

        self.config.logger.info("🛑 Shutting down status update queue...")
        if self.update_queue:
            try:
                await self.update_queue.join()  # Wait for all enqueued tasks to complete
            except asyncio.CancelledError:
                self.config.logger.debug("Status update queue join was cancelled")
            self.config.logger.info("✅ Status update queue shutdown complete.")

    async def _get_current_status(self) -> bool:
        """
        Function to get retrieve all pods that have been create, check their status,
        enqueue events to the update_queue for each active pod found.
        """
        if self.config is None:
            self.config = _get_config()
        try:
            pod_list = await call_list_namespaced_pod(
                namespace=self.config.default_namespaces[0],
                # use pod_label_name_test and pod_label_value_text from config because
                # we know this is always on a pod that is created by the operator
                label_selector=f"{self.config.pod_label_name_text}={self.config.pod_label_value_text}"
            )
            if pod_list is None or not pod_list.items:
                self.config.logger.info("No existing pods found for status check.")
                return True # This is still a success
            
            for pod in pod_list.items:
                if pod.metadata and pod.metadata.labels:
                    if (
                        pod.metadata.deletion_timestamp is None
                        and "symphony.requestId" in pod.metadata.labels
                    ):
                        pod_status = await get_pod_status(pod)
                        update_event = UpdateEvent(
                            cr_name=pod.metadata.labels.get("app", ""),
                            namespace=pod.metadata.namespace or self.config.default_namespaces[0],
                            pod_name=pod.metadata.name or "",
                            pod_status={"phase": pod_status},
                            request_id=pod.metadata.labels.get("symphony.requestId", ""),
                        )
                        await enqueue_status_update(update_event)
                        self.config.logger.info(
                            f"Enqueued status update for existing pod {pod.metadata.name} with status {pod_status}"
                        )
            return True
        except Exception as e:
            self.config.logger.error(f"Error listing pods for status check: {e}")
            return False
        

def create_status_update_queue(
    config: Config,
) -> tuple[aio_queue.Queue[Any], asyncio.Event]:
    """
    Creates a queue for GCPSymphonyResource status updates.
    """
    config.logger.debug("Creating status update queue and stop event...")
    update_queue: aio_queue.Queue = aio_queue.Queue()
    stop_event = asyncio.Event()
    config.logger.debug("Status update queue and stop event created successfully.")
    return update_queue, stop_event


@log_execution_time(_get_config().logger)
async def enqueue_status_update(
    update_event: UpdateEvent, update_queue: Optional[aio_queue.Queue] = None
) -> None:
    """
    Enqueues a GCPSymphonyResource status update.
    """
    if update_queue is None:
        context = get_op_context()
        update_queue = await context.get_update_queue()  # type: ignore

    if update_queue is not None:
        await update_queue.put(update_event.model_dump())
    else:
        raise RuntimeError("Update queue is not initialized.")


async def get_gcpsymphonyresource_phase(
    request_id: str,
    namespace: str,
    logger: Logger,
    config: Config,
    phases: list[str] | None = None,
) -> tuple[str, int]:
    """
    Calculate the overall phase of the GCPSymphonyResource based on the machines' statuses.
    """

    if not request_id or len(request_id) < config.min_request_id_length:
        logger.error(
            f"Request ID {request_id} is too short, skipping phase calculation"
        )
        return "Unknown", 0

    if phases is not None:
        return await _calculate_phase(phases)

    # A list of phases wasn't supplied, so we need to fetch the pods
    try:
        machines_list = await call_list_namespaced_pod(
            namespace=namespace, label_selector=f"symphony.requestId={request_id}"
        )
        # if no pods are found, call _calculate_phase with an empty list
        if not machines_list.items:
            return await _calculate_phase([])

        # Filter pods in a single pass, checking pod conditions
        active_pods = []
        for pod in machines_list.items:
            if pod.metadata.deletion_timestamp is None:
                pod_status = await get_pod_status(pod)
                active_pods.append(pod_status)

        result = await _calculate_phase(active_pods)
        return result

    except ApiException as e:
        logger.error(f"Error listing pods: {e}")
        return "Error", 0


async def get_pod_status(pod: V1Pod) -> str:
    """
    Determines the overall status of a pod based on its conditions and phase.
    """
    if not pod.status:
        return PodPhase.UNKNOWN

    if pod.status.conditions:
        # check for "Ready" condition first (highest precedence)
        for condition in pod.status.conditions or []:
            if condition.type == PodConditionType.READY and condition.status == "True":
                return PodPhase.RUNNING

        # check for "Disrupted" condition second (medium precedence)
        for condition in pod.status.conditions or []:
            if (
                condition.type == PodConditionType.DISRUPTED
                and condition.status == "True"
            ):
                return PodPhase.TERMINATING
        # IF no "Ready" or "Disrupted" condition, return a not-ready phase
        return PodPhase.NOT_READY

    # If there's no conditions, fall back to the pod's phase
    return pod.status.phase or PodPhase.UNKNOWN


async def _calculate_phase(machines: list[str]) -> tuple[str, int]:
    """Helper function to calculate phase from a list of machine states."""

    running_count = sum(1 for machine in machines if machine == ResourcePhase.RUNNING)
    if len(machines) == 0:
        return ResourcePhase.WAITING_CLEANUP, running_count
    if all(machine == PodPhase.RUNNING for machine in machines):
        return ResourcePhase.RUNNING, running_count
    if any(machine in [PodPhase.TERMINATING, PodPhase.FAILED] for machine in machines):
        return ResourcePhase.DEGRADED, running_count
    if any(machine in [PodPhase.PENDING, PodPhase.NOT_READY] for machine in machines):
        return ResourcePhase.PENDING, running_count

    return ResourcePhase.UNKNOWN, running_count
