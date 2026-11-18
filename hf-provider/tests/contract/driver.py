import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

from jsonschema.validators import validator_for

_CONTRACT_DIR = Path(__file__).resolve().parent
_SCHEMA_DIR = _CONTRACT_DIR / "schemas"
_RESOURCES = _CONTRACT_DIR.parent / "resources"


class Cli:
    """A provider CLI that the driver runs as a subprocess."""

    def __init__(
        self,
        module: str,
        env: dict[str, str],
        log_dir: Path,
        payload_dir: Path,
        stub_launcher: Optional[Path] = None,
    ) -> None:
        self.module = module
        self.env = env
        self.payload_dir = payload_dir
        self.stub_launcher = stub_launcher
        host = env["EGOSC_INSTANCE_HOST"]
        self.log_file = log_dir / f"gcp-symphony-provider.{host}.log"
        self._payload_seq = 0

    def _write_payload(self, payload: Any) -> Path:
        self._payload_seq += 1
        path = self.payload_dir / f"payload-{self._payload_seq}.json"
        path.write_text(json.dumps(payload))
        return path

    def _payload_args(self, payload: Any, payload_path: Optional[Path]) -> list[str]:
        """Build the -f argument the wrapper scripts pass."""
        if payload is not None and payload_path is not None:
            raise ValueError("pass at most one of payload, payload_path")

        if payload_path is not None:
            return ["-f", str(payload_path)]
        if payload is not None:
            return ["-f", str(self._write_payload(payload))]
        return []

    def run(
        self,
        *args: str,
        payload: Any = None,
        payload_path: Optional[Path] = None,
        stubbed: bool = False,
        timeout: int = 180,
    ) -> subprocess.CompletedProcess[str]:
        """Run the CLI as a subprocess."""
        argv = [*args, *self._payload_args(payload, payload_path)]

        if stubbed:
            if self.stub_launcher is None:
                raise ValueError(f"no stub launcher configured for {self.module}")
            program = [sys.executable, str(self.stub_launcher)]
        else:
            program = [sys.executable, "-m", self.module]

        return subprocess.run(
            [*program, *argv],
            capture_output=True,
            text=True,
            env=self.env,
            timeout=timeout,
            check=False,
        )


def resource_payload(relative: str) -> Path:
    """Give the path to a sample request in tests/resources."""
    path = _RESOURCES / relative
    if not path.is_file():
        raise FileNotFoundError(f"missing sample payload: {path}")
    return path


def assert_matches_schema(instance: Any, schema_name: str) -> None:
    """Validate a response against a schema in tests/contract/schemas."""
    schema = json.loads((_SCHEMA_DIR / schema_name).read_text())
    validator_cls = validator_for(schema)
    validator_cls.check_schema(schema)

    errors = list(validator_cls(schema).iter_errors(instance))
    if errors:
        details = "\n".join(
            f"  at {list(error.absolute_path)}: {error.message}" for error in errors
        )
        raise AssertionError(f"{schema_name} validation failed:\n{details}\n  instance: {instance}")
