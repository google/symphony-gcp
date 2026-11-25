import json
import shutil
from pathlib import Path
from typing import Any, Optional

import pytest
from contract.driver import Cli

from gke_provider.config import (
    DEFAULT_CRD_GROUP,
    DEFAULT_CRD_KIND,
    DEFAULT_CRD_PLURAL,
    DEFAULT_CRD_RETURN_REQUEST_KIND,
    DEFAULT_CRD_RETURN_REQUEST_PLURAL,
    DEFAULT_CRD_VERSION,
    DEFAULT_NAMESPACE,
)

from contract.gke_provider.stub_launcher import CLUSTER_STATE_PATH_ENV

SEEDED_REQUEST_ID = "contract-seeded-request"
SEEDED_MACHINE_NAME = "gcontract-seeded-request-0001"
PENDING_REQUEST_ID = "contract-pending-request"
PENDING_MACHINE_NAME = "gcontract-pending-request-0001"
SEEDED_RETURN_REQUEST_ID = "contract-seeded-return-request"
RETURNED_MACHINE_NAME = "gcontract-returned-0001"

_START_TIME = "2026-08-01T12:00:00+00:00"

_STUB_LAUNCHER = Path(__file__).resolve().parent / "stub_launcher.py"

_POD_DEFAULTS: dict[str, Any] = {
    "name": None,
    "uid": None,
    "namespace": DEFAULT_NAMESPACE,
    "labels": None,
    "phase": None,
    "pod_ip": None,
    "start_time": None,
}


def _custom_object(
    kind: str, name: str, request_id: str, status: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """Build a custom resource as the Kubernetes API gives it."""
    obj = {
        "apiVersion": f"{DEFAULT_CRD_GROUP}/{DEFAULT_CRD_VERSION}",
        "kind": kind,
        "metadata": {
            "name": name,
            "namespace": DEFAULT_NAMESPACE,
            "labels": {"symphony.requestId": request_id},
        },
        "spec": {},
    }
    if status is not None:
        obj["status"] = status
    return obj


def _read_cluster_state(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _write_cluster_state(path: Path, state: dict[str, Any]) -> None:
    path.write_text(json.dumps(state))


def _add_custom_object(state_path: Path, plural: str, obj: dict[str, Any]) -> None:
    """Add one custom resource to the cluster state file."""
    state = _read_cluster_state(state_path)
    state["custom_objects"].setdefault(plural, []).append(obj)
    _write_cluster_state(state_path, state)


def _add_pod(state_path: Path, **fields: object) -> None:
    """Add one pod to the cluster state file."""
    unknown = set(fields) - set(_POD_DEFAULTS)
    if unknown:
        raise ValueError(f"unknown pod fields: {sorted(unknown)}")

    state = _read_cluster_state(state_path)
    state["pods"].append({**_POD_DEFAULTS, **fields})
    _write_cluster_state(state_path, state)


class GkeCli(Cli):
    """Driver for hf-gke, with the cluster state file the stubbed commands read."""

    def __init__(
        self,
        env: dict[str, str],
        log_dir: Path,
        payload_dir: Path,
        cluster_state_path: Path,
    ) -> None:
        super().__init__(
            module="gke_provider",
            env=env,
            log_dir=log_dir,
            payload_dir=payload_dir,
            stub_launcher=_STUB_LAUNCHER,
        )
        self.cluster_state_path = cluster_state_path


@pytest.fixture
def gke_cli(tmp_path: Path, make_cli_env, provider_config_dir: Path) -> GkeCli:
    """Give an hf-gke CLI with its own config, cluster state file, and log directory."""
    conf_dir = tmp_path / "conf"
    shutil.copytree(provider_config_dir / "gcpgkeinst", conf_dir)

    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    payload_dir = tmp_path / "payloads"
    payload_dir.mkdir()

    cluster_state_path = tmp_path / "cluster-state.json"
    _write_cluster_state(cluster_state_path, {"custom_objects": {}, "pods": []})

    env = make_cli_env(conf_dir, log_dir)
    env[CLUSTER_STATE_PATH_ENV] = str(cluster_state_path)
    return GkeCli(
        env=env, log_dir=log_dir, payload_dir=payload_dir, cluster_state_path=cluster_state_path
    )


@pytest.fixture
def seeded_request(gke_cli: GkeCli) -> str:
    """Add one request with a running pod to the cluster state file and give its request id."""
    _add_custom_object(
        gke_cli.cluster_state_path,
        DEFAULT_CRD_PLURAL,
        _custom_object(DEFAULT_CRD_KIND, "gcontract-seeded-request-", SEEDED_REQUEST_ID),
    )
    _add_pod(
        gke_cli.cluster_state_path,
        name=SEEDED_MACHINE_NAME,
        uid="contract-pod-uid-1",
        labels={"symphony.requestId": SEEDED_REQUEST_ID},
        phase="Running",
        pod_ip="10.0.0.5",
        start_time=_START_TIME,
    )
    return SEEDED_REQUEST_ID


@pytest.fixture
def pending_request(gke_cli: GkeCli) -> str:
    """Add one request with a pending pod to the cluster state file and give its request id."""
    _add_custom_object(
        gke_cli.cluster_state_path,
        DEFAULT_CRD_PLURAL,
        _custom_object(DEFAULT_CRD_KIND, "gcontract-pending-request-", PENDING_REQUEST_ID),
    )
    _add_pod(
        gke_cli.cluster_state_path,
        name=PENDING_MACHINE_NAME,
        uid="contract-pod-uid-2",
        labels={"symphony.requestId": PENDING_REQUEST_ID},
        phase="Pending",
    )
    return PENDING_REQUEST_ID


@pytest.fixture
def seeded_return_request(gke_cli: GkeCli) -> str:
    """Add one completed return request to the cluster state file and give its request id."""
    _add_custom_object(
        gke_cli.cluster_state_path,
        DEFAULT_CRD_RETURN_REQUEST_PLURAL,
        _custom_object(
            DEFAULT_CRD_RETURN_REQUEST_KIND,
            "mrr-contract-seeded-return-request-",
            SEEDED_RETURN_REQUEST_ID,
            status={"phase": "Completed"},
        ),
    )
    return SEEDED_RETURN_REQUEST_ID


@pytest.fixture
def seeded_returned_machine(gke_cli: GkeCli) -> str:
    """Add one returned machine to the cluster state file and give its name."""
    _add_custom_object(
        gke_cli.cluster_state_path,
        DEFAULT_CRD_PLURAL,
        _custom_object(
            DEFAULT_CRD_KIND,
            "gcontract-returned-request-",
            "contract-returned-request",
            status={
                "returnedMachines": [
                    {"name": RETURNED_MACHINE_NAME, "returnRequestId": "contract-return-1"}
                ]
            },
        ),
    )
    return RETURNED_MACHINE_NAME
