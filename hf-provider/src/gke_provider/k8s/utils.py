"""Utility functions for the API endpoints."""

import uuid
from logging import Logger
from typing import Optional

from kubernetes import client as k8s
from kubernetes.client import ApiException

from common.utils.profiling import log_execution_time
from gke_provider.config import get_config


def generate_unique_id(length: int = 64) -> str:
    """
    Generates a unique, random identifier that is 16 characters long.
    """
    if length < 4:
        raise ValueError("Length must be at least 4")
    return str(uuid.uuid4())[:length]


@log_execution_time(get_config().logger)
def get_gcpsymphonyresource_phase(
    request_id: str,
    namespace: str,
    core_v1: k8s.CoreV1Api,
    logger: Logger,
    phases: Optional[list[str]] = None,
) -> tuple[str, int]:
    """
    Calculate the overall phase of the GCPSymphonyResource based on the machines' statuses.
    """
    result = "Unknown"
    if request_id is not None and len(request_id) < 10:
        logger.debug(f"Request ID {request_id} is too short, skipping phase calculation")
    else:
        try:
            if phases is None:
                machines_list = core_v1.list_namespaced_pod(
                    namespace=namespace,
                    label_selector=f"symphony.requestId={request_id}",
                )
                if not machines_list:
                    result = "NotAvailable"
                    raise ApiException(status=404, reason="No pods found for this request ID")

                machines = [pod.status.phase for pod in machines_list.items]
            else:
                machines = phases
            all_running = all(machine == "Running" for machine in machines)
            any_succeeded = any(machine == "Succeeded" for machine in machines)
            any_failed = any(machine == "Failed" for machine in machines)
            any_pending = any(machine == "Pending" for machine in machines)

            if any_pending:
                result = "Pending"
            elif any_failed:
                result = "Degraded"
            elif all_running or any_succeeded:
                result = "Running"
            else:
                result = "Unknown"
        except ApiException as e:
            logger.error(f"Error listing pods: {e}")

    return (
        result,
        len([count for count, machine in enumerate(machines) if machine == "Running"]),
    )
