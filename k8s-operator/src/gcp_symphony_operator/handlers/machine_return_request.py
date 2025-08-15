import asyncio
import datetime
import enum
from logging import Logger
from typing import Any, Dict, Optional

import kopf
from gcp_symphony_operator.config import Config
from gcp_symphony_operator.k8s.core_v1 import (
    call_delete_namespaced_pod,
    call_list_namespaced_pod,
    call_patch_namespaced_pod,
)
from gcp_symphony_operator.k8s.custom_objects import (
    call_patch_namespaced_custom_object,
    call_patch_namespaced_custom_object_status,
)
from kubernetes.client import ApiException


class MachineStatusEvents(str, enum.Enum):
    """
    Enum for machine status events used in MachineReturnRequest.
    """

    PENDING = "Pending"
    IN_PROGRESS = "InProgress"
    COMPLETED = "Completed"
    FAILED = "Failed"
    PARTIALLY_COMPLETED = "PartiallyCompleted"


async def create_machine_event() -> Dict[str, Any]:
    """
    Create a machine event dictionary with the current timestamp.
    This is used to initialize machine events in the MachineReturnRequest status.
    """
    current_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return {
        "returnRequestTime": current_time,
        "status": MachineStatusEvents.PENDING.value,
        "message": "Return request received",
    }

async def process_pod_delete(delete_request_id: str, machine_id: str, namespace: str):
    # patch the pod being returned so that the delete_handler can get the
    # delete request ID and remove the finalizer to speed up deletion
    patch_body = {
        "metadata": {
            "labels": {"symphony.returnRequestId": delete_request_id}
        }
    }
    try:
        await call_patch_namespaced_pod(
            name=machine_id,
            namespace=namespace,
            body=patch_body,
        )  # type: ignore
        
        # delete the pod
        await call_delete_namespaced_pod(
            name=machine_id,
            namespace=namespace,
        )  # type: ignore
    except Exception | ApiException as e:
        raise
    

def machine_return_request_handler_factory(config: Config, logger: Logger) -> Any:
    """
    Factory function to create a handler for MachineReturnRequest custom resources.
    This handler processes MachineReturnRequest resources to delete pods from a GCPSymphonyResource.
    """

    # initialize the Kubernetes clients for this handler
    # This is done here to ensure that the clients are created in the same event loop
    # as the handler, avoiding issues with asyncio and threading.
    @kopf.on.create(
        plural=config.crd_return_request_plural,
        group=config.crd_group,
        version=config.crd_api_version,
    )  # type: ignore
    async def machine_return_request_create_handler(
        meta: Dict[str, Any],
        spec: Dict[str, Any],
        status: Optional[Dict[str, Any]],
        logger: Logger,
        **kwargs: Any,
    ) -> Dict | None:
        """
        Handle the creation of a MachineReturnRequest custom resource.
        This function is called when a MachineReturnRequest CR is created.
        It validates the request and initiates the pod deletion process.
        """
        request_id = spec.get("requestId")
        machine_ids = spec.get("machineIds", [])

        if not request_id or not machine_ids or len(machine_ids) < 1:
            err = f"Missing required fields in MachineReturnRequest spec:\n{spec}"
            logger.error(err)
            return {
                "phase": "Failed",
                "totalMachines": 0,
                "returnedMachines": 0,
                "failedMachines": 0,
                "conditions": [
                    {
                        "type": "Failed",
                        "status": "True",
                        "lastTransitionTime": datetime.datetime.now(
                            datetime.timezone.utc
                        ).isoformat(),
                        "reason": "RequestValidationFailed",
                        "message": f"The request is invalid: {err}",
                    }
                ],
                "machineEvents": {},
            }

        # Initialize status
        total_machines = len(machine_ids)
        machine_events = {}
        current_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
        logger.debug(
            f"Creating machine_events for {total_machines} machines at {current_time}."
        )
        for machine_id in machine_ids:
            # create machineEvents items for the MRR status
            machine_events[machine_id] = {
                "returnRequestTime": current_time,
                "status": "Pending",
                "message": "Return request received",
            }

        # Set initial status of the MachineReturnRequest
        initial_status = {
            "phase": "InProgress",
            "totalMachines": total_machines,
            "returnedMachines": 0,
            "failedMachines": 0,
            "conditions": [
                {
                    "type": "Processing",
                    "status": "True",
                    "lastTransitionTime": current_time,
                    "reason": "DeletionStarted",
                    "message": f"Starting deletion of {total_machines} machines",
                }
            ],
            "machineEvents": machine_events,
        }

        logger.info(
            f"MachineReturnRequest {meta['name']} "
            f"created with requestId {request_id} for {total_machines} machines"
        )

        try:
            # Update the status of the MachineReturnRequest
            await call_patch_namespaced_custom_object_status(
                namespace=meta["namespace"],
                name=meta["name"],
                plural=config.crd_return_request_plural,
                patch_body={"status": initial_status},
            )
        except ApiException as e:
            logger.error(
                f"Error updating status for {meta['kind']}: {meta['name']}: {e}"
            )
            return initial_status

        # schedule a task to update the resource after a short delay
        async def trigger_update():
            await asyncio.sleep(0.1)  # small delay to ensure the resource is created
            try:
                # Make a small update to trigger the update handler
                await call_patch_namespaced_custom_object(
                    namespace=meta["namespace"],
                    name=meta["name"],
                    plural=config.crd_return_request_plural,
                    patch_body={"metadata": {"labels": {"triggerUpdate": "true"}}},
                )
                logger.debug(f"Triggered update to for {meta['name']}")
            except ApiException as e:
                logger.error(f"Error triggering update: {e}")

        # Start the task but don't wait for it to complete
        asyncio.create_task(trigger_update())

        return

    @kopf.on.resume(
        plural=config.crd_return_request_plural,
        group=config.crd_group,
        version=config.crd_api_version,
    )  # type: ignore
    @kopf.on.update(
        plural=config.crd_return_request_plural,
        group=config.crd_group,
        version=config.crd_api_version,
    )  # type: ignore
    @kopf.on.field(
        plural=config.crd_return_request_plural,
        group=config.crd_group,
        version=config.crd_api_version,
        field="metadata.labels.triggerUpdate",
    )  # type: ignore
    async def machine_return_request_update_handler(
        meta: Dict[str, Any],
        spec: Dict[str, Any],
        status: Optional[Dict[str, Any]],
        logger: Logger,
        **kwargs: Any,
    ) -> Dict[str, Any] | None:
        """
        Handle updates to a MachineReturnRequest custom resource.
        This function processes the actual pod deletion based on the request.
        """
        if not status:
            # If no status exists, let the create handler initialize it
            return None
        mse = MachineStatusEvents

        # If the request is already completed or failed, don't process it again
        current_phase = status.get("phase", "")
        if current_phase in [mse.COMPLETED, mse.FAILED]:
            return None
        delete_request_id = meta.get("labels", {}).get("symphony.requestId", "unknown")
        machine_ids = spec.get("machineIds", [])

        # Get current machine events or initialize if not present
        machine_events = status.get("machineEvents", {})
        completed_count = 0
        failed_count = 0

        pod_selector = f"managed-by={config.operator_name}"
        existing_pods = await call_list_namespaced_pod(
            namespace=meta["namespace"],
            label_selector=pod_selector,
        )
        existing_pod_names = (
            [
                p.metadata.name
                for p in existing_pods.items
                if p.metadata and p.metadata.name
            ]
            if existing_pods and existing_pods.items
            else []
        )

        # Process each machine for deletion
        for machine_id in machine_ids:
            if machine_id in existing_pod_names:
                # Skip if already completed or failed
                if machine_id in machine_events and machine_events[machine_id].get(
                    "status"
                ) in [mse.COMPLETED, mse.FAILED]:
                    if machine_events[machine_id].get("status") == mse.COMPLETED:
                        completed_count += 1
                    else:
                        failed_count += 1
                    continue

                # Update status to InProgress for this machine
                current_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
                if machine_id not in machine_events:
                    machine_events[machine_id] = {
                        "machineId": machine_id,
                        "returnRequestTime": current_time,
                        "status": mse.IN_PROGRESS,
                        "message": "Processing return request",
                    }
                else:
                    machine_events[machine_id]["status"] = mse.IN_PROGRESS
                    machine_events[machine_id]["message"] = "Processing return request"


                try:
                    await process_pod_delete(
                        delete_request_id=delete_request_id,
                        machine_id=machine_id,
                        namespace=meta.get("namespace", config.default_namespaces[0]),
                    )
                except ApiException as e:
                    if e.status == 404:
                        # Pod already deleted, mark as completed
                        machine_events[machine_id]["status"] = mse.COMPLETED
                        machine_events[machine_id]["returnCompletionTime"] = (
                            datetime.datetime.now(datetime.timezone.utc).isoformat()
                        )
                        machine_events[machine_id][
                            "message"
                        ] = "Pod was already returned"
                        completed_count += 1
                    else:
                        # Failed to delete pod
                        machine_events[machine_id]["status"] = mse.FAILED
                        machine_events[machine_id][
                            "message"
                        ] = f"Failed to return pod: {e.reason}"
                        failed_count += 1
                        logger.error(f"Error deleting pod {machine_id}: {e}")
            else:
                # If the pod does not exist, mark as completed
                # so it's properly tracked on the MRR and on the GCPSR
                if machine_id not in machine_events:
                    machine_events[machine_id] = {
                        "machineId": machine_id,
                        "returnRequestTime": datetime.datetime.now(
                            datetime.timezone.utc
                        ).isoformat(),
                        "status": mse.COMPLETED,
                        "message": "Pod does not exist, marked as completed",
                    }
                else:
                    machine_events[machine_id]["status"] = mse.COMPLETED
                    machine_events[machine_id][
                        "message"
                    ] = "Pod does not exist, marked as completed"
                completed_count += 1
        # Determine overall phase
        total_machines = len(machine_ids)
        if completed_count + failed_count == total_machines:
            if failed_count == 0:
                phase = mse.COMPLETED
                reason = "AllPodsDeleted"
                message = f"Successfully returned all {completed_count} pods"
            elif completed_count == 0:
                phase = mse.FAILED
                reason = "AllPodsFailed"
                message = f"Failed to return all {failed_count} pods"
            else:
                phase = mse.PARTIALLY_COMPLETED
                reason = "SomePodsDeleted"
                message = f"Returned {completed_count} pods, {failed_count} pods failed"
        else:
            phase = mse.IN_PROGRESS
            reason = "DeletionInProgress"
            message = (
                f"Returned {completed_count} pods, "
                f"{failed_count} failed, "
                f"{total_machines - completed_count - failed_count} pending"
            )

        logger.debug(
            f"Updating MachineReturnRequest {meta['name']} status: "
            f"phase={phase}, "
            f"totalMachines={total_machines}, "
            f"returnedMachines={completed_count}, "
            f"failedMachines={failed_count}, "
            f"reason={reason}, "
            f"message={message}"
        )
        labels = meta.get("labels", {}).copy()
        if phase in [mse.COMPLETED, mse.FAILED]:
            labels["symphony.waitingCleanup"] = str(True)
            if labels["triggerUpdate"]:
                del labels["triggerUpdate"]
            logger.info(
                f"MachineReturnRequest {meta['name']} completed with status: {phase}"
            )

        # Patch the MachineReturnRequest metadata to set the proper labels
        # This is to ensure that the MachineReturnRequest is marked for cleanup
        try:
            await call_patch_namespaced_custom_object(
                namespace=meta["namespace"],
                name=meta["name"],
                plural=config.crd_return_request_plural,
                patch_body={"metadata": {"labels": labels}},
            )

        except ApiException as e:
            logger.error(f"Error updating labels for {meta['name']}: {e}")
        # Patch the status of the MachineReturnRequest
        try:
            patch_body = {
                "status": {
                    "phase": phase,
                    "totalMachines": total_machines,
                    "returnedMachines": completed_count,
                    "failedMachines": failed_count,
                    "conditions": [
                        {
                            "type": reason,
                            "status": "True",
                            "lastTransitionTime": datetime.datetime.now(
                                datetime.timezone.utc
                            ).isoformat(),
                            "reason": reason,
                            "message": message,
                        }
                    ],
                    "machineEvents": machine_events,
                }
            }
            await call_patch_namespaced_custom_object_status(
                namespace=meta["namespace"],
                name=meta["name"],
                plural=config.crd_return_request_plural,
                patch_body=patch_body,
            )
        except ApiException as e:
            err = f"Failed to update MachineReturnRequest status: {e}"
            logger.error(err)

    # machine_return_request_handler_factory function returns
    return machine_return_request_create_handler, machine_return_request_update_handler
