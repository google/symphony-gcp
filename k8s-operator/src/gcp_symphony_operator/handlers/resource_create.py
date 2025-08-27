import asyncio
import datetime
import uuid
from logging import Logger
from typing import Any, Dict, List

import kopf
from gcp_symphony_operator.api.v1.types.gcp_symphony_resource import (
    Condition,
    GCPSymphonyResource,
    GCPSymphonyResourceSpec,
    GCPSymphonyResourceStatus,
)
from gcp_symphony_operator.config import Config
from gcp_symphony_operator.k8s.core_v1 import call_create_pod
from gcp_symphony_operator.k8s.custom_objects import (
    call_patch_namespaced_custom_object,
    call_patch_namespaced_custom_object_status,
)
from gcp_symphony_operator.profiling import log_execution_time
from kubernetes.client import (
    ApiException,
    V1ObjectMeta,
    V1OwnerReference,
    V1Pod,
)


def resource_create_handler_factory(config: Config, logger: Logger) -> Any:

    @log_execution_time(logger)
    @kopf.on.create(config.crd_group, config.crd_api_version, config.crd_plural)  # type: ignore
    async def create_gcpsymphonyresource(
        spec: Dict[str, Any],
        meta: Dict[str, Any],
        status: Dict[str, Any],
        logger: Logger,
        uid: str,
        **kwargs: Any | None,
    ) -> None:
        """
        Handle the creation of a GCPSymphonyResource custom resource.

        This function is called when a GCPSymphonyResource is created.
        It deploys pods based on the spec and meta information.
        """
        if meta.get("uid", None) is None:
            meta["uid"] = uid
        gcpsr: GCPSymphonyResource = GCPSymphonyResource(
            spec=GCPSymphonyResourceSpec(**spec),
            metadata=meta,
            status=GCPSymphonyResourceStatus(**status),
        )
        name = gcpsr.metadata.get("name", "unknown")
        namespace = gcpsr.metadata.get("namespace", config.default_namespaces[0])
        request_id = gcpsr.metadata.get("labels", {}).get("symphony.requestId")
        if not request_id:
            logger.warning(
                "Request ID not found in labels, this resource was not created "
                "by the API, generating a requestID"
            )
            # generate a uuid
            request_id = f"{config.request_id_internal_prefix}{str(uuid.uuid4())}"

        # Deploy pods based on the spec and meta information
        pod_list = await _deploy_pods(gcpsr, config, request_id, logger)

        # update the metadata with the request ID if we had to create it here
        if request_id.startswith("int-"):
            patch_body = {
                "metadata": {
                    "labels": {"symphony.requestId": request_id},
                }
            }
            try:
                await call_patch_namespaced_custom_object(
                    namespace=namespace, name=name, patch_body=patch_body
                )
            except Exception as e:
                logger.error(
                    f"Error updating {config.crd_kind} {name}"
                    f"metadata with internal request ID: {e}"
                )

        # Update the status of the custom resource
        gcpsr_status = GCPSymphonyResourceStatus(
            phase="Pending",
            availableMachines=0,  # Initially set to 0, will be updated later
            conditions=[
                Condition(
                    type="PodsCreated",
                    status="True",
                    reason="PodsCreated",
                    message=(
                        "Pods created: "
                        f"{len([p for p in pod_list if p['status'] == 'created'])}, "
                        "failed: "
                        f"{len([p for p in pod_list if p['status'] != 'created'])}"
                    ),
                    lastTransitionTime=datetime.datetime.now(
                        datetime.timezone.utc
                    ).isoformat(),
                ),
            ],
        )
        patch_body = gcpsr_status.model_dump()
        try:
            await call_patch_namespaced_custom_object_status(
                namespace=namespace, name=name, patch_body=patch_body
            )
            logger.debug(
                f"{config.crd_kind} {meta['name']} status updated with pods created"
            )
        except Exception as e:
            logger.error(f"Error updating {config.crd_kind} {meta['name']} status: {e}")

    @log_execution_time(logger)
    async def _deploy_pods(
        gcpsr: GCPSymphonyResource,
        config: Config,
        request_id: str,
        logger: Logger,
    ) -> List[Dict[str, Any]]:
        """
        Deploy pods based on the spec and meta information.
        This function creates a list of pods based on the provided specification
        and metadata. The pods are created with the specified container image,
        ports, labels, and annotations. The function returns a list of dictionaries
        representing the created pods.
        Args:
            spec (Dict[str, Any]): A dictionary containing the pod specifications.
                - image (str): Container image to use.
                - containerPort (int): Port exposed by the container.
                - hostPort (int): Port exposed on the host.
                - pod_count (int): Number of pods to create.
                - ...other elements...
            meta (Dict[str, Any]): A dictionary containing metadata for the pods.
                - name (str): Name of the pods.
                - namespace (str): Namespace where the pods will be created.
                - annotations (dict, optional): Annotations to add to the pods.
                - labels (dict, optional): Labels to add to the pods.
                - ...other elements...
            config: Operator configuration
            logger: Logger instance
            max_workers (int): Maximum number of threads/processes to use.
        Returns:
            list[Dict[str, Any]]: A list of dictionaries representing the created pods.
        """

        """---------------------------------------------------------------------
        #?   start internal function for creating individual pods
        ---------------------------------------------------------------------"""

        def _create_pod_body(i: int) -> V1Pod:
            """
            Create a single pod body.
            """
            labels = gcpsr.metadata.get("labels", {})
            if not labels:
                # Add default labels if none are on the custom resource
                labels = {
                    "symphony.requestId": request_id,
                    config.pod_label_name_text: config.pod_label_value_text
                }
            pod_name = f"{gcpsr.metadata['name']}-pod-{i}"
            pod_spec = gcpsr.spec.podSpec
            # if the pod spec provided does not have a termination grace period,
            # use the default grace period from the config
            if not hasattr(pod_spec, "default_grace_period") or (
                hasattr(pod_spec, "default_grace_period")
                and pod_spec["default_grace_period"] is None
            ):
                pod_spec["default_grace_period"] = config.default_pod_grace_period
            logger.debug(f"\n\npod_spec = {pod_spec}\n\n")
            pod_body = V1Pod(
                api_version="v1",
                kind="Pod",
                metadata=V1ObjectMeta(
                    name=pod_name,
                    namespace=gcpsr.metadata["namespace"],
                    owner_references=[
                        V1OwnerReference(
                            api_version=f"{config.crd_group}/{config.crd_api_version}",
                            kind=config.crd_kind,
                            name=gcpsr.metadata["name"],
                            uid=gcpsr.metadata["uid"],
                            controller=True,
                            block_owner_deletion=True,
                        )
                    ],
                    labels={
                        "app": gcpsr.metadata["name"],
                        "managed-by": config.operator_name,
                        **(labels),
                    },
                    annotations=(gcpsr.metadata.get("annotations", {})),
                ),
                spec=pod_spec,
            )

            return pod_body

        """---------------------------------------------------------------------
        #? end internal function for creating individual pods
        ---------------------------------------------------------------------"""

        pod_count = gcpsr.spec.machineCount or config.default_minimum_machine_count
        batch_size = config.pod_create_batch_size

        pod_bodies = []
        pod_list = []
        for i in range(pod_count):
            pod_bodies.append(_create_pod_body(i))

        for i in range(0, len(pod_bodies), batch_size):
            batch = pod_bodies[i : i + batch_size]
            for pod_body in batch:
                try:
                    # Create fresh client for this operation to avoid event loop issues
                    pod = await call_create_pod(
                        pod_body=pod_body, namespace=gcpsr.metadata["namespace"]
                    )
                    if isinstance(pod, V1Pod) and pod.metadata and pod.metadata.name:
                        logger.debug(f"Pod: {pod.metadata.name} created")
                        pod_list.append(
                            {"name": pod.metadata.name, "status": "created"}
                        )
                    else:
                        logger.warning(f"Pod object does not have metadata.name: {pod}")
                        pod_list.append({"name": "unknown", "status": "created"})
                except asyncio.TimeoutError:
                    logger.error(
                        f"Timeout while creating pod {pod_body.metadata.name} "
                        f"in namespace {gcpsr.metadata['namespace']}"
                    )
                except ApiException as e:
                    logger.error(f"Error creating pod {pod_body.metadata.name}: {e}")
                    pod_list.append(
                        {
                            "name": pod_body.metadata.name,
                            "status": "failed",
                            "error": str(e),
                        }
                    )
        return pod_list

    return create_gcpsymphonyresource
