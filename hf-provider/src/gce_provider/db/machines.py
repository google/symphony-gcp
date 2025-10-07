import sqlite3
from types import SimpleNamespace
from typing import Any, Callable, Optional

import google.cloud.compute_v1 as compute
from tenacity import retry, stop_after_attempt, wait_exponential

from common.model.models import HFReturnRequestsResponse
from common.utils.list_utils import flatten
from gce_provider.config import Config, get_config
from gce_provider.db.gce_helpers import (
    extract_instance_ips,
    fetch_instances,
    parse_resource_url,
)
from gce_provider.db.transaction import Statement, Transaction
from gce_provider.model.models import HfMachine, HfMachineStatus, ResourceIdentifier
from gce_provider.utils.constants import MachineState
from gce_provider.utils.instances import set_instance_labels


def _generate_instance_creation_params(instance: compute.Instance):
    instance_ips = extract_instance_ips(instance)
    return {
        "machine_name": instance.name,
        "internal_ip": instance_ips.internal_ip or None,
        "external_ip": instance_ips.external_ip or None,
    }


class MachineDao:
    def __init__(self, config: Optional[Config] = None):
        if config is None:
            config = get_config()
        self.config = config
        self.logger = config.logger

    def store_request_machines(
        self,
        operation_id: str,
        request: compute.InstanceGroupManagersCreateInstancesRequest,
    ) -> None:
        """Store an HF requestMachines request"""
        params = list(
            map(
                lambda x: {
                    "machine_name": x.name,
                    "request_id": request.request_id,
                    "operation_id": operation_id,
                    "instance_group_manager": request.instance_group_manager,
                    "gcp_zone": request.zone,
                },
                request.instance_group_managers_create_instances_request_resource.instances,
            )
        )

        with Transaction(self.config) as trans:
            trans.executemany(
                [
                    Statement(
                        # @formatter:off
                        """
                        INSERT INTO machines
                        (machine_name, request_id, operation_id, instance_group_manager, gcp_zone)
                        VALUES
                        (:machine_name,
                         :request_id,
                         :operation_id,
                         :instance_group_manager,
                         :gcp_zone)
                        """,
                        params,
                    )
                ],
            )

    def store_delete_machines(
        self,
        request_id: str,
        operation_id: str,
        request: compute.InstanceGroupManagersDeleteInstancesRequest,
    ) -> None:
        """Store an HF requestReturnMachines request"""
        machines = [
            parse_resource_url(instance)
            for instance in request.instance_group_managers_delete_instances_request_resource.instances  # noqa: E501
        ]
        params = list(
            map(
                lambda x: {
                    "machine_name": x.name,
                    "return_request_id": request_id,
                    "delete_operation_request_id": request.request_id,
                    "delete_operation_id": operation_id,
                },
                machines,
            )
        )

        query = """
                UPDATE machines
                SET return_request_id=:return_request_id,
                    delete_operation_id=:delete_operation_id,
                    delete_operation_request_id=:delete_operation_request_id
                WHERE machine_name=:machine_name"""
        with Transaction(self.config) as trans:
            trans.executemany(
                [
                    Statement(
                        query,
                        params,
                    )
                ],
            )

    class RetryRequired(RuntimeError):
        """Indicates that a retry is requred"""

        pass

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(10)
    )
    def _update_instance_ips(self, message: SimpleNamespace) -> None:
        operation_id = message.operation.id
        self.logger.info(f"Updating instance IPs for operation {operation_id}")

        query = """
            SELECT machine_name, gcp_zone
            FROM machines
            WHERE operation_id=?
              AND internal_ip IS NULL
              AND machine_state >= ?
            """

        with sqlite3.connect(self.config.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                query,
                (operation_id, MachineState.CREATED.value),
            )
            rows = cur.fetchall()

            machines_needing_ip = [
                ResourceIdentifier(
                    project=self.config.gcp_project_id, zone=zone, name=machine_name
                )
                for machine_name, zone in rows
            ]

        self.logger.debug(
            f"We are missing IP address for {len(machines_needing_ip)} machines."
        )

        # get the IP addresses for each machine
        instances = fetch_instances(machines_needing_ip)
        params = [
            _generate_instance_creation_params(instance) for instance in instances
        ]

        query = (
            "UPDATE machines "
            "SET internal_ip=:internal_ip, external_ip=:external_ip "
            "WHERE machine_name=:machine_name"
        )
        with Transaction(self.config) as trans:
            trans.executemany(
                [
                    Statement(
                        query,
                        params,
                    )
                ],
            )

        # these exceptions should trigger a retry
        if len(instances) < len(machines_needing_ip):
            msg = f"Only {len(instances)} machines found, of {len(machines_needing_ip)} needed."
            self.logger.debug(msg)
            raise MachineDao.RetryRequired(msg)

        for param in params:
            if not param["internal_ip"]:
                msg = "At least one machine does not yet have its IP assigned"
                self.logger.debug(msg)
                raise MachineDao.RetryRequired(msg)

        self.logger.info(
            f"Successfully updated IP address for operation {operation_id}"
        )

    def _handle_instances_created(
        self, message: SimpleNamespace
    ) -> Callable[[SimpleNamespace], None]:
        """Update machine state to reflect that instances were created"""
        self.logger.info(
            f"Handling instance creation for operation {message.operation.id}"
        )

        request = message.protoPayload.request
        machine_names = [x.name for x in request.instances]
        # strip the gcp zone from the url provided by the client message
        zone = message.protoPayload.response.zone.split("/")[-1]
        machine_name_param = ",".join("?" for _ in machine_names)
        with Transaction(self.config) as trans:
            trans.execute(
                [
                    Statement(
                        "UPDATE MACHINES "
                        f"SET machine_state={MachineState.CREATED.value} "
                        f"WHERE machine_name IN ({machine_name_param})",
                        machine_names,
                    )
                ],
            )

        # update the labels for the instances
        if (
            len(
                failed_instances := set_instance_labels(
                    request.instances, zone, self.config
                )
            )
            > 0
        ):
            self.logger.warning(
                "Failed to set labels for instance(s): "
                f"{', '.join(failed_instances)}"
            )

        self.logger.info(
            f"Finished handling instance creation for operation {message.operation.id}"
        )

        # this callback can happen after the message is acknowledged
        return self._update_instance_ips

    def _handle_group_instances_deleted(self, message: SimpleNamespace) -> None:
        """Update machine state to reflect that group instances were deleted"""
        self.logger.info(
            f"Handling instance deletion for operation {message.operation.id}"
        )

        request = message.protoPayload.request
        resources = [parse_resource_url(x) for x in request.instances]
        machine_names = [x.name for x in resources]

        machine_name_param = ",".join("?" for _ in machine_names)
        with Transaction(self.config) as trans:
            trans.execute(
                [
                    Statement(
                        "UPDATE MACHINES SET "
                        f"machine_state={MachineState.DELETED.value} "
                        f"WHERE machine_name IN ({machine_name_param})",
                        machine_names,
                    )
                ],
            )

        self.logger.info(
            f"Finished handling instance deletion for operation {message.operation.id}"
        )

        return None

    def _handle_instance_deleted(self, message: SimpleNamespace) -> None:
        """Update machine state to reflect that some instance was deleted"""
        self.logger.info(
            f"Handling instance deletion for operation {message.operation.id}"
        )

        # we convert to a list just in case in the future we need to support multiple values
        resource_urls = [message.protoPayload.resourceName]
        resources = [parse_resource_url(x) for x in resource_urls]
        operation_id = message.operation.id
        machine_names = [x.name for x in resources]
        params = flatten([operation_id, machine_names])
        machine_name_param = ",".join("?" for _ in machine_names)
        with Transaction(self.config) as trans:
            trans.execute(
                [
                    Statement(
                        f"""
                        UPDATE machines
                        SET machine_state={MachineState.DELETED.value},
                            delete_operation_id=?,
                            delete_grace_period=0
                        WHERE machine_name IN ({machine_name_param})""",
                        params,
                    )
                ],
            )

        self.logger.info(
            f"Finished handling instance deletion for operation {message.operation.id}"
        )

        return None

    def _handle_instance_preempted(self, message: SimpleNamespace) -> None:
        """Update machine state to reflect that some instance was deleted"""

        # this function is written prospectively based on published documentation,
        # but needs to be tested
        self.logger.info(
            f"Handling instance deletion for operation {message.operation.id}"
        )

        # we convert to a list just in case in the future we need to support multiple values
        resource_urls = [message.protoPayload.resourceName]
        resources = [parse_resource_url(x) for x in resource_urls]
        operation_id = message.operation.id
        machine_names = [x.name for x in resources]
        params = flatten([operation_id, machine_names])
        machine_name_param = ",".join("?" for _ in machine_names)
        with Transaction(self.config) as trans:
            trans.execute(
                [
                    Statement(
                        # default (and possibly universal) grace period is 30 seconds
                        f"""
                        UPDATE machines
                        SET machine_state={MachineState.PREEMPTED.value}, delete_grace_period=30
                        WHERE machine_name IN ({machine_name_param})""",
                        params,
                    )
                ],
            )

        self.logger.info(
            f"Finished handling instance preemption for operation {message.operation.id}"
        )

        return None

    def _handle_instances_logged(self, message: SimpleNamespace) -> None:
        operation_id = message.operation.id
        with Transaction(self.config) as trans:
            trans.execute(
                [
                    Statement(
                        "UPDATE MACHINES "
                        f"SET machine_state={MachineState.LOGGED.value} "
                        f"WHERE machine_state < {MachineState.LOGGED.value} and operation_id = ?",
                        [operation_id],
                    )
                ],
            )

    def update_machine_state(
        self, message: SimpleNamespace
    ) -> Optional[Callable[[SimpleNamespace], Any]]:
        """
        Update a machine request based on a message from PubSub. May optionally
        return a callback function that can be called after the message is acknowledged,
        to perform post-processing
        """

        # guard against messages that cannot be handled
        if not (
            hasattr(message, "operation")
            and hasattr(message.operation, "id")
            and hasattr(message, "protoPayload")
        ):
            self.logger.debug(
                f"Ignoring unsupported message {message.insertId} from {message.logName}"
            )
            return None

        # grab the request payload.
        try:
            if hasattr(message.protoPayload, "response"):
                response = message.protoPayload.response

                try:
                    request = message.protoPayload.request
                except Exception:
                    request = None

                self.logger.debug(f"Checking request {request}, response {response}")
                operation_type = response.operationType

                # check to see if instances have been created
                if operation_type == "compute.instanceGroupManagers.createInstances":
                    return self._handle_instances_created(message)

                # check to see if instances have been deleted by the Instance Group Manager
                elif operation_type == "compute.instanceGroupManagers.deleteInstances":
                    return self._handle_group_instances_deleted(message)

                # check to see if any of my managed instances was deleted outside
                # the Instance Group Manager
                elif operation_type == "delete":
                    return self._handle_instance_deleted(message)

                # check to see if any of my managed instances was preempted
                elif operation_type == "compute.instances.preempted":
                    self.logger.info(f"Got a preemption {message}")
                    return self._handle_instance_preempted(message)

                # no match
                else:
                    self.logger.debug(
                        f"Ignoring unhandled operation type {operation_type}"
                    )
            else:
                self.logger.debug("Ignoring message with no response entity")

        except Exception as e:
            self.logger.error(e)
            raise e
        return None

    def get_machines_for_request(self, request_id: str) -> list[HfMachineStatus]:
        query = """
                SELECT *
                FROM machines
                WHERE (request_id=:request_id OR return_request_id=:request_id)
                """

        with sqlite3.connect(
            self.config.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        ) as conn:
            cur = conn.cursor()
            cur.execute(
                query,
                {"request_id": request_id},
            )
            rows = cur.fetchall()
            columns = [col[0] for col in cur.description]
            machines: list[HfMachineStatus] = [
                HfMachineStatus(**dict(zip(columns, row))) for row in rows
            ]
            return machines

    def get_machines_by_name(self, machine_names: list[str]) -> list[HfMachine]:
        """Return a list of machines matching the names provided"""
        machine_name_param = ",".join("?" for _ in machine_names)

        query = f"""
                SELECT *
                FROM machines
                WHERE machine_name IN ({machine_name_param})
                """

        with sqlite3.connect(
            self.config.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        ) as conn:
            cur = conn.cursor()
            cur.execute(
                query,
                machine_names,
            )
            rows = cur.fetchall()
            columns = [col[0] for col in cur.description]
            machines: list[HfMachine] = [
                HfMachine(**dict(zip(columns, row))) for row in rows
            ]
            return machines

    def get_deleted_or_preempted_machines(
        self,
    ) -> list[HFReturnRequestsResponse.Request]:
        """Gets all deleted or preempted machines that have no associated return requests"""
        query = f"""
                SELECT machine_name, delete_grace_period
                FROM machines
                WHERE return_request_id IS NULL
                AND machine_state IN (?, ?)
                """
        with sqlite3.connect(
            self.config.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        ) as conn:
            cur = conn.cursor()
            cur.execute(
                query, (MachineState.PREEMPTED.value, MachineState.DELETED.value)
            )
            rows = cur.fetchall()
            return [
                HFReturnRequestsResponse.Request(machine=row[0], gracePeriod=row[1])
                for row in rows
            ]
