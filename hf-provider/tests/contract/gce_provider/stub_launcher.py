import warnings
from typing import Any


class _StubOperation:
    name = "contract-stub-operation"


class _StubInstanceGroupManagersClient:
    """Stand in for compute.InstanceGroupManagersClient without the network."""

    def create_instances(self, _request: Any = None, **_kwargs: Any) -> _StubOperation:
        # Used by the #86 warning test.
        warnings.warn("contract-canary: warning raised inside the provider")
        return _StubOperation()

    def delete_instances(self, _request: Any = None, **_kwargs: Any) -> _StubOperation:
        return _StubOperation()


def _install_stub() -> None:
    """Replace the Compute client factory with the stub client."""
    from gce_provider.utils import client_factory

    client_factory.instance_group_managers_client = lambda *_args, **_kwargs: (
        _StubInstanceGroupManagersClient()
    )


def main() -> None:
    """Run the real CLI with the stub client installed."""
    from common.log_bootstrap import bootstrap_logging

    bootstrap_logging()

    _install_stub()

    from gce_provider.__main__ import main as cli_main

    cli_main()


if __name__ == "__main__":
    main()
