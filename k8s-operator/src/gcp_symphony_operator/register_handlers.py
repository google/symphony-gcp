"""
Handler registry for the GCP Symphony Kubernetes Operator.
This module provides a centralized way to register and retrieve kopf handlers.
"""

from gcp_symphony_operator.config import Config

# Store for registered handlers
_resource_handlers = {
    "create": [],
    "update": [],
    "container_state": [],
    "resume": [],
    "timer": [],
    "field": [],
}


def register_handlers(config: Config) -> None:
    """
    Register all handlers with kopf using the provided configuration.
    This should be called after Config is fully initialized.
    """
    logger = config.logger
    logger.info("Registering kopf event handlers")

    # Import handlers here to avoid circular imports
    from gcp_symphony_operator.handlers import (
        container_state_change,
        machine_return_request,
        pod_delete,
        resource_create,
        resource_update,
    )

    # Resource create handlers
    _resource_handlers["create"] = resource_create.resource_create_handler_factory(
        config, logger
    )

    # Resource update handlers
    _resource_handlers["update"] = resource_update.resource_update_handler_factory(
        config, logger
    )

    # Container state handlers
    _resource_handlers["container_state"] = (
        container_state_change.container_state_handler_factory(config, logger)
    )

    _resource_handlers["pod_delete"] = pod_delete.pod_delete_handler_factory(
        config, logger
    )

    _resource_handlers["mrr"] = (
        machine_return_request.machine_return_request_handler_factory(config, logger)
    )

    if config.enable_gke_preemption_handling:
        from gcp_symphony_operator.handlers import preemption
        _resource_handlers["preemption"] = preemption.preemption_handler_factory(
            config, logger
        )

    logger.info("All handlers registered successfully")
