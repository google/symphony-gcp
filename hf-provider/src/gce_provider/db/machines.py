import sqlite3
import asyncio
from types import SimpleNamespace
from typing import Any, Callable, Optional, Dict, Tuple

import google.cloud.compute_v1 as compute
from tenacity import retry, stop_after_attempt, wait_exponential, wait_random
from debouncer import debounce, DebounceOptions

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
        wait=wait_exponential(multiplier=1, min=1, max=60),
        stop=stop_after_attempt(1000),
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
        """Update machine state to reflect that instances were created within the managed group.
        Note, this does not necessarily mean they exist yet"""
        self.logger.info(
            f"Handling instance creation for operation {message.operation.id}"
        )

        request = message.protoPayload.request
        machine_names = [x.name for x in request.instances]
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

        self.logger.info(
            f"Finished handling instance creation for operation {message.operation.id}"
        )
        # this callback can happen after the message is acknowledged
        return self._handle_instances_created_callback

    def _handle_instances_created_callback(self, message: SimpleNamespace):
        request = message.protoPayload.request
        # strip the gcp zone from the url provided by the client message
        zone = message.protoPayload.response.zone.split("/")[-1]

        self._update_instance_ips(message)

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
            f"Finished handling instance creation callback for operation {message.operation.id}"
        )

    def _handle_instances_inserted(
        self, message: SimpleNamespace
    ) -> Callable[[SimpleNamespace], None]:
        """Update machine state to reflect that instances were created"""
        operation_id = message.operation.id

        self.logger.info(f"Handling instance insertion for operation {operation_id}")

        # we convert to a list just in case in the future we need to support multiple values
        resource_urls = [message.protoPayload.resourceName]
        resources = [parse_resource_url(x) for x in resource_urls]
        machine_names = [x.name for x in resources]
        machine_name_param = ",".join("?" for _ in machine_names)
        with Transaction(self.config) as trans:
            trans.execute(
                [
                    Statement(
                        f"""
                        UPDATE machines
                        SET machine_state={MachineState.INSERTED.value}
                        WHERE machine_name IN ({machine_name_param})
                        AND machine_state<{MachineState.INSERTED.value}""",
                        machine_names,
                    )
                ],
            )

        self.logger.info(
            f"Finished handling instance insertion for operation {message.operation.id}"
        )

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
                        f"machine_state={MachineState.DELETE_REQUESTED.value} "
                        f"WHERE machine_name IN ({machine_name_param})",
                        machine_names,
                    )
                ],
            )

        self.logger.info(
            f"Finished handling instance deletion for operation {message.operation.id}"
        )

        # Check if auto trim command is enabled
        if self.config.auto_run_trim_db:
            # Check for possible cleanup of expired returned machines
            self.remove_expired_returned_machines()

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

        # Check if auto trim command is enabled
        if self.config.auto_run_trim_db:
            # Check for possible cleanup of expired returned machines
            self.remove_expired_returned_machines()

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

                # check to see if instances have been inserted
                if operation_type == "insert":
                    return self._handle_instances_inserted(message)

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

    def check_or_raise(self) -> None:
        """
        Fast pre-flight check:
            - DB reachable and writable
            - Table exists
            - DB integrity quick check passes
            - Insert/Delete capability sanity (within a rollback)
        Raisess a RuntimeError with a short message if something looks wrong
        """
        ok, details = self._quick_check()
        if not ok:
            err = "DB quick check failed: " + "; ".join(
                f"{i}={j}" for i, j in details.items() if j not in (True, "ok")
            )
            self.logger.error(err)
            raise RuntimeError(err)

    def _quick_check(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Return (ok, details) where the details include:
            - table_exists (boolean)
            - writable (boolean)
            - integrity (ok or error text)
            - insert_ok (boolean) # False if schema required values
            - delete_ok (boolean) # True when insert_ok is True
            - needs_required_values (boolean)
        We just used SAVEPOINT/ROLLBACK and never commit any changes
        """

        details: Dict[str, Any] = {
            "table_exists": False,
            "writable": False,
            "integrity": "unknown",
            "insert_ok": False,
            "delete_ok": False,
            "needs_required_values": False,
        }

        try:
            with sqlite3.connect(
                self.config.db_path,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            ) as conn:
                cur = conn.cursor()
                cur.execute("PRAGMA busy_timeout=2000")

                # Step 1: Verify Table Existence
                self.logger.debug("Step 1: Verify Table Existence")
                cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='machines'"
                )
                details["table_exists"] = cur.fetchone() is not None
                if not details["table_exists"]:
                    details["integrity"] = "machines table missing"
                    return (False, details)

                # Step 2: Check writable permission (Ensure file is writable)
                self.logger.debug(
                    "Step 2: Check writable permission (Ensure file is writable)"
                )
                try:
                    cur.execute("BEGIN IMMEDIATE")
                    details["writable"] = True
                    conn.rollback()
                except sqlite3.OperationalError as e:
                    details["integrity"] = f"Not Writable: {e}"
                    self.logger.error(details["integrity"])
                    return (False, details)

                # Step 3: Integrity Check
                self.logger.debug("Step 3: Integrity Check")
                try:
                    cur.execute("PRAGMA quick_check")
                    row = cur.fetchone()
                    details["integrity"] = (
                        "ok"
                        if (row and row[0] == "ok")
                        else (row[0] if row else "unknown")
                    )
                    if details["integrity"] != "ok":
                        return (False, details)
                except sqlite3.DatabaseError as e:
                    details["integrity"] = f"Quick Check Error: {e}"
                    # self.logger.error(details["integrity"])
                    return (False, details)

                # Step 4: Insert/Delete probe inside SAVEPOINT (rollback always)
                self.logger.debug(
                    "Step 4: Insert/Delete probe inside SAVEPOINT (rollback always)"
                )
                try:
                    # Check Insert
                    cur.execute("SAVEPOINT check_tx")
                    cur.execute("INSERT INTO machines DEFAULT VALUES")
                    rowId = cur.lastrowid
                    details["insert_ok"] = True

                    # Check Delete
                    cur.execute("DELETE FROM machines WHERE rowid = ?", (rowId,))
                    details["delete_ok"] = cur.rowcount == 1
                except sqlite3.IntegrityError:
                    details["needs_required_values"] = True
                except sqlite3.OperationalError as e:
                    details["integrity"] = f"Insert/Delete Operational Error: {e}"
                    self.logger.error(details["integrity"])
                    conn.execute("ROLLBACK TO check_tx")
                    conn.execute("RELEASE check_tx")
                    return (False, details)
                finally:
                    try:
                        conn.execute("ROLLBACK TO check_tx")
                        conn.execute("RELEASE check_tx")
                    except sqlite3.OperationalError:
                        pass
                self.logger.debug("[DONE] - DB is healthy")
                return (True, details)  # means db is healthy :)

        except sqlite3.Error as e:
            details["integrity"] = f"Connection Error: {e}"
            self.logger.error(details["integrity"])
            return (False, details)

    @debounce(wait=5.0, options=DebounceOptions(trailing=False, leading=True))  
    async def _remove_expired_returned_machines_async(self) -> int:
        """Asynchronously delete machine rows where return_ttl has expired."""

        def _blocking_db_work():
            selectQuery = f"""
                SELECT machine_name
                    FROM machines
                WHERE machine_state IN ({MachineState.DELETED.value}, {MachineState.DELETE_REQUESTED.value})
                    AND delete_grace_period = 0
                AND DATETIME(updated_at, '+{self.config.returned_vm_ttl} days') <= CURRENT_TIMESTAMP
            """

            with sqlite3.connect(
                self.config.db_path,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            ) as conn:
                cur = conn.cursor()
                cur.execute(selectQuery)
                candidate_for_deletion = [row[0] for row in cur.fetchall()]

            if not candidate_for_deletion:
                self.logger.debug("No expired returned machines found for cleanup.")
                return 0

            deleted_count = len(candidate_for_deletion)

            placeholders = ", ".join(["?"] * deleted_count)
            deleteQuery = f"DELETE FROM machines WHERE machine_name IN ({placeholders})"

            with Transaction(self.config) as trans:
                trans.execute(
                    [
                        Statement(deleteQuery, candidate_for_deletion)
                    ]
                )

            return deleted_count
    
        deleted_count = await asyncio.to_thread(_blocking_db_work)
        self.logger.info(f"Successfully cleaned up {deleted_count} expired returned machines.")
        return deleted_count

    def remove_expired_returned_machines(self) -> int:
        """Delete machine rows where return_ttl has expired."""
        try:
            l = asyncio.get_event_loop()
            if l.is_running():
                asyncio.create_task(self._remove_expired_returned_machines_async())
                return 0
            else:
                return asyncio.run(self._remove_expired_returned_machines_async())
        except RuntimeError:
            # No event loop in current thread
            return asyncio.run(self._remove_expired_returned_machines_async())
        except Exception as e:
            self.logger.error(f"Error during cleanup of expired returned machines: {e}")
            return 0