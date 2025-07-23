import datetime
from logging import Logger
from typing import Any, Dict, List, Optional

import kopf
from gcp_symphony_operator.api.v1.types.gcp_symphony_resource import Condition
from gcp_symphony_operator.config import Config
from gcp_symphony_operator.k8s.custom_objects import call_get_custom_object
from gcp_symphony_operator.workers.status_update import (
    UpdateEvent,
    enqueue_status_update,
)
from kubernetes.client import ApiException, V1PodStatus


def pod_delete_handler_factory(config: Config, logger: Logger) -> Any:
    def get_return_request_id(meta: dict) -> str:
        """
        Get the delete request ID from the pod metadata.
        This function retrieves the delete request ID from the pod metadata labels.
        """
        request_id: str = meta.get("labels", {}).get("symphony.returnRequestId", None)
        if request_id is None:
            logger.error(f"Pod {meta['name']} has no returnRequestId label")
        return request_id

    @kopf.on.delete("v1", "pod", labels={"managed-by": config.operator_name})  # type: ignore
    async def pod_delete_handler(
        meta: Dict[str, Any],
        spec: Optional[Dict[str, Any]],
        status: Optional[Dict[str, Any]],
        old: Optional[List[Dict[str, Any]]],
        new: Optional[List[Dict[str, Any]]],
        diff: Optional[Dict[str, Any]],
        logger: Logger,
        **kwargs: Any,
    ) -> Any:
        """
        Handle the deletion of a pod managed by this operator.
        This function is called when a pod managed by this operator is deleted.
        It updates the custom resource status based on the pod deletion.
        """
        err = None

        # get the ownerRefernence name to find the GCPSymphonyResource to update
        owner = meta.get("labels", {}).get("app", None)
        if owner is None:
            err = f"Pod {meta['name']} has no owner reference"
            logger.error(err)
        else:
            # Validate there is a request ID on the deleted pod
            request_id = meta.get("labels", {}).get("symphony.requestId", None)
            if request_id is None:
                err = f"Pod {meta['name']} has no request ID label"
                logger.error(err)
                raise kopf.TemporaryError(err, delay=5)
            # Try to get the custom resource that owns the deleted pod
            owner_resource = None
            try:
                owner_resource = await call_get_custom_object(
                    name=owner,
                    namespace=meta["namespace"],
                    plural=config.crd_plural,
                )
            except ApiException as e:
                # Handle the case where the owner resource is not found
                # (probably deleted already)
                if e.status == 404:
                    logger.warning(
                        f"{config.crd_kind} {owner} not found, kopf should handle, "
                        f"but double check and make sure pod {meta['name']} has been deleted"
                    )
                else:
                    err = f"Error updating {config.crd_kind} {owner}: {e}"
                    logger.error(err)
                return  # No need to do anything else here, Kopf will handle the deletion

            # We should have th owner resource now, if not, raise an error
            if owner_resource is None:
                err = f"Owner resource {owner} of kind {config.crd_kind} not found"
                raise ApiException(reason=err)

            owner_metadata = (
                owner_resource["metadata"]
                if isinstance(owner_resource, dict) and "metadata" in owner_resource
                else {}
            )

            if owner_metadata is not None and isinstance(owner_metadata, dict):
                if "markedForDeletion" in owner_metadata:
                    # If the owner resource is marked for deletion, we don't need to update it
                    logger.debug(
                        f"{config.crd_kind}: {owner} is marked for deletion, skipping update."
                    )
                    return

            # Add this pod to the list of deleted pods in the owner resource's status
            if (
                isinstance(owner_resource, dict)
                and "status" in owner_resource
                and isinstance(owner_resource["status"], dict)
            ):
                owner_status = owner_resource["status"]
            else:
                owner_status = {}

            if not isinstance(owner_status, dict) or owner_status is None:
                owner_status = {}
            if "returnedMachines" not in owner_status:
                owner_status["returnedMachines"] = []
            deleted_pods = owner_status.get("returnedMachines", [])
            # if the deleted pod doesn't have a returnRequestId label,
            # use the system initiated return message to indicate it was
            # deleted by the kubernetes control plane (or manually)
            return_request_id = (
                get_return_request_id(meta) or config.system_initiated_return_msg
            )
            returned_hostnames = [p.get("name") for p in deleted_pods]
            if meta["name"] not in returned_hostnames:
                deleted_pods.append(
                    {
                        "name": meta["name"],
                        "returnRequestId": return_request_id,
                        "returnTime": datetime.datetime.now(
                            datetime.timezone.utc
                        ).isoformat(),
                    }
                )
            owner_status["returnedMachines"] = deleted_pods

            # Prepare a new condition for the pod deletion
            new_condition = Condition(
                type="PodReturned",
                status="True",  # Or some other appropriate status
                lastTransitionTime=datetime.datetime.now(
                    datetime.timezone.utc
                ).isoformat(),
                reason="Returned",
                message=f"Pod {meta['name']} has been returned",
            )
            # Set that status.phase of the pod to "Returned"
            pod_status = status.to_dict() if isinstance(status, V1PodStatus) else {}
            pod_status["phase"] = "Returned"
            # trim out any empty ReturnedMachine entries in deleted_pods
            deleted_pods = [
                rp
                for rp in deleted_pods
                if rp.get("name") and rp.get("returnRequestId")
            ]
            update_event: UpdateEvent = UpdateEvent(
                cr_name=owner,
                namespace=meta["namespace"],
                new_condition=new_condition,
                pod_name=meta["name"],
                pod_status=pod_status,
                returned_machines=deleted_pods,
                request_id=request_id,
            )

            # Enqueue the status update
            await enqueue_status_update(update_event)
            logger.info(
                f"Enqueued status update for pod {meta['name']} "
                f"deletion in custom resource {owner}"
            )

    return pod_delete_handler
