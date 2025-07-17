import argparse
import asyncio
import logging
import os
import sys
import traceback

from .config import Config
from .controller import run_operator
from .manifests import Manifests
from .register_handlers import register_handlers
from .utils import check_operator_setup

# Add the parent directory of the module to sys.path if not already present
module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if module_path not in sys.path:
    sys.path.append(module_path)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="GCP Symphony Operator.")
    subparsers = parser.add_subparsers(dest="action")

    export_parser = subparsers.add_parser(
        "export-manifests",
        help="Perform an action: export-manifests",
    )
    export_parser.add_argument(
        "--separate-files",
        type=str,
        required=False,
        help="Export each manifest to a separate file (only applies to export-manifests action).",
    )
    return parser.parse_args()


def main() -> None:
    """Main function to run the operator directly (not using kopf CLI)."""

    args = parse_args()

    if args.action == "export-manifests":
        # Export manifests to files and exit
        manifests = Manifests()
        manifests.export_manifest(
            target_path=args.separate_files,
            separate_files=(args.separate_files is not None),
        )
        return

    # Initialize the config object after export-manifests functionality
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    config: Config = loop.run_until_complete(Config.create())

    # set the logging level for the kubernetes client
    # defaults to DEFAULT_LOGGING_LEVEL unless environment variable
    # *KUBERNETES_CLIENT_LOG_LEVEL is set
    logging.getLogger("kubernetes").setLevel(config.kubernetes_client_log_level)

    try:
        # Ensure the environment is setup before starting operator
        loop.run_until_complete(check_operator_setup(config, config.logger))
        config.logger.info(
            f"Starting Google Symphony Operator version {config.operator_version}"
        )
        register_handlers(config)
        # Run the operator
        run_operator(config, config.logger)

    except Exception as e:
        config.logger.error(f"failed to start operator: {e}")
        config.logger.debug(f"Stack trace: {traceback.format_exc()}")
        raise


if __name__ == "__main__":
    main()
