import json
import shutil
import sqlite3
from pathlib import Path
from typing import Any

import pytest
from contract.driver import Cli

from gce_provider.config import DEFAULT_DB_FILENAME
from gce_provider.utils.constants import MachineState

SEEDED_REQUEST_ID = "contract-seeded-request"
SEEDED_MACHINE_NAME = "sym-contract-0001"
RETURNED_MACHINE_NAME = "sym-contract-returned-0001"

_ZONE = "us-central1-c"
_INSTANCE_GROUP = "contract-instance-group"
_TIMESTAMP = "2026-08-01 12:00:00"

_STUB_LAUNCHER = Path(__file__).resolve().parent / "stub_launcher.py"

_INSERT_MACHINE = """
    INSERT INTO machines (
        machine_name, request_id, gcp_zone, instance_group_manager,
        machine_state, operation_id, internal_ip, external_ip,
        delete_grace_period, created_at, updated_at
    ) VALUES (
        :machine_name, :request_id, :gcp_zone, :instance_group_manager,
        :machine_state, :operation_id, :internal_ip, :external_ip,
        :delete_grace_period, :created_at, :updated_at
    )
"""

_MACHINE_DEFAULTS: dict[str, Any] = {
    "machine_name": None,
    "request_id": None,
    "gcp_zone": _ZONE,
    "instance_group_manager": _INSTANCE_GROUP,
    "machine_state": None,
    "operation_id": None,
    "internal_ip": None,
    "external_ip": None,
    "delete_grace_period": None,
    "created_at": _TIMESTAMP,
    "updated_at": _TIMESTAMP,
}


def _insert_machine(db_path: Path, **columns: Any) -> None:
    """Add one row to the machines table."""
    unknown = set(columns) - set(_MACHINE_DEFAULTS)
    if unknown:
        raise ValueError(f"unknown machines columns: {sorted(unknown)}")

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(_INSERT_MACHINE, {**_MACHINE_DEFAULTS, **columns})
        conn.commit()
    finally:
        conn.close()


class GceCli(Cli):
    """Driver for hf-gce, with the SQLite database the status commands read."""

    def __init__(
        self,
        env: dict[str, str],
        log_dir: Path,
        payload_dir: Path,
        db_dir: Path,
    ) -> None:
        super().__init__(
            module="gce_provider",
            env=env,
            log_dir=log_dir,
            payload_dir=payload_dir,
            stub_launcher=_STUB_LAUNCHER,
        )
        self.db_path = db_dir / DEFAULT_DB_FILENAME

    def initialize_db(self) -> None:
        """Make the database that the status commands read."""
        result = self.run("initializeDB")
        assert (
            result.returncode == 0
        ), f"initializeDB failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"


@pytest.fixture
def gce_cli(tmp_path: Path, make_cli_env, provider_config_dir: Path) -> GceCli:
    """Give an hf-gce CLI with its own config, database, and log directory."""
    conf_dir = tmp_path / "conf"
    shutil.copytree(provider_config_dir / "gcpgceinst", conf_dir)

    config_path = conf_dir / "gcpgceinstprov_config.json"
    provider_conf = json.loads(config_path.read_text())
    provider_conf["PUBSUB_AUTOLAUNCH"] = False
    config_path.write_text(json.dumps(provider_conf))

    db_dir = tmp_path / "db"
    db_dir.mkdir()
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    payload_dir = tmp_path / "payloads"
    payload_dir.mkdir()

    env = make_cli_env(conf_dir, log_dir)
    env["HF_DBDIR"] = str(db_dir)
    return GceCli(env=env, log_dir=log_dir, payload_dir=payload_dir, db_dir=db_dir)


@pytest.fixture
def seeded_request(gce_cli: GceCli) -> str:
    """Add one machine to the database and give its request id."""
    gce_cli.initialize_db()

    _insert_machine(
        gce_cli.db_path,
        machine_name=SEEDED_MACHINE_NAME,
        request_id=SEEDED_REQUEST_ID,
        machine_state=MachineState.CREATED.value,
        operation_id="contract-operation-1",
        internal_ip="10.0.0.5",
        external_ip="34.1.2.3",
    )
    return SEEDED_REQUEST_ID


@pytest.fixture
def seeded_returned_machine(gce_cli: GceCli) -> str:
    """Add one deleted machine to the database and give its name."""
    gce_cli.initialize_db()

    _insert_machine(
        gce_cli.db_path,
        machine_name=RETURNED_MACHINE_NAME,
        request_id="contract-returned-request",
        machine_state=MachineState.DELETED.value,
        operation_id="contract-operation-2",
        delete_grace_period=0,
    )
    return RETURNED_MACHINE_NAME
