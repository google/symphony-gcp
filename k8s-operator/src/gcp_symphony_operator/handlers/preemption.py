import enum
import uuid
from logging import Logger
from typing import Any

import kopf
from gcp_symphony_operator.config import get_config
from gcp_symphony_operator.k8s.core_v1 import call_list_pod_for_namespace_on_node
from gcp_symphony_operator.k8s.custom_objects import (
    call_create_namespaced_custom_object,
)


class PreemptionKeys(str, enum.Enum):
    """
    Enum for preemption keys used in GKE.
    """

    GKE_SPOT_LABELS = [
        "cloud.google.com/gke-spot=true",
        "cloud.google.com/gke-provisioning=spot",
    ]
    NODE_TAINTS_LIST = [
        "DeletionCandidateOfClusterAutoscaler",
        "node.cloudprovider.kubernetes.io/shutdown",
    ]


def preemption_handler_factory(config, logger: Logger) -> Any:
    """
    Factory function to create the preemption handler.

    Args:
        config: The configuration object.
        logger: The logger instance.

    Returns:
        A function that handles node preemption events.
    """

    @kopf.on.field("v1", "node", field="spec.taints")  # type: ignore
    async def handle_node_preemption(
        old: list[dict] | None,
        new: list[dict] | None,
        name: str,
        labels: dict[str, str] | None = None,
        status: dict[str, str] | None = None,
        logger: Logger | None = None,
        **kwargs,
    ):
        """
        Handle node preemption events by checking for GKE Spot nodes.
        """
        config = await get_config()
        logger = config.logger

        # check if this is a spot VM
        if not labels:
            return

        # Check to see if any of the label selectors in PremptionKeys.GKE_SPOT_LABELS list
        # are present in the node labels.
        if not any(label in labels for label in PreemptionKeys.GKE_SPOT_LABELS.value):
            logger.debug(
                f"Node {name} is not a GKE Spot VM. Skipping preemption handling."
            )
            return

        logger.debug(f"Processing taints for node {name}")
        logger.debug(f"Old taints: {old}")
        logger.debug(f"New taints: {new}")

        # Look for impending termination taint
        old_taints = old or []
        new_taints = new or []

        # check if termination taint was added
        old_has_termination = any(
            t.get("key") in PreemptionKeys.NODE_TAINTS_LIST.value for t in old_taints
        )
        new_has_termination = any(
            t.get("key") in PreemptionKeys.NODE_TAINTS_LIST.value for t in new_taints
        )

        if not old_has_termination and new_has_termination:
            logger.info(
                "Spot VM node {name} is being preempted. Gracefully terminating pods."
            )

            field_selector = f"spec.nodeName={name}"
            label_selectors = f"managed-by={config.operator_name}"
            try:
                pods = await call_list_pod_for_namespace_on_node(
                    field_selector=field_selector,
                    label_selector=label_selectors,
                    namespace=config.default_namespaces[0],
                )
            except Exception as e:
                logger.error(f"Failed to list pods for node {name}: {e}")
                raise kopf.TemporaryError(f"Failed to list pods: {e}", delay=5)

            if pods and pods.items:
                # Create a MachineReturnRequest custom resource to handle
                # gracefully terminating pods and recording them
                pods_list = pods.items
                machine_list: list[str] = [
                    p.metadata.name
                    for p in pods_list  # type: ignore
                    if p.metadata
                    and p.metadata.name
                    and p.status
                    and p.status.phase == "Running"
                ]
                logger.debug(
                    f"Found {len(machine_list)} running pods on node {name} to terminate."
                )
                logger.debug(f"Pods to terminate: {machine_list}")
                if machine_list:
                    # Create a MachineReturnRequest custom resource
                    request_id = str(uuid.uuid4())[:64]  # Generate a unique request ID
                    meta_name = (
                        f"{config.preempted_machine_request_id_prefix}{request_id}"
                    )
                    namespace = config.default_namespaces[0]
                    new_label = {"symphony.requestId": request_id}
                    resource_body = {
                        "apiVersion": f"{config.crd_group}/{config.crd_api_version}",
                        "kind": config.crd_return_request_kind,
                        "metadata": {
                            "generateName": f"{meta_name}-",
                            "namespace": namespace,
                            "labels": new_label,
                        },
                        "spec": {
                            "requestId": meta_name,
                            "machineIds": machine_list,
                            "labels": new_label,
                        },
                    }
                    if hasattr(resource_body, "items:"):
                        resource_body = dict(resource_body)
                    logger.debug(
                        "Node Preemption! Creating MachineReturnRequest: "
                        f"{resource_body}"
                    )
                    try:
                        await call_create_namespaced_custom_object(
                            body=resource_body,
                            plural=config.crd_return_request_plural,
                            namespace=namespace,
                        )
                    except Exception as e:
                        message = f"Failed to create MachineReturnRequest: {e}"
                        logger.error(message)
                        raise kopf.TemporaryError(message, delay=5)

    # preemption handler factory return
    return handle_node_preemption
