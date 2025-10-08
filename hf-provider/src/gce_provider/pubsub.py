import json
import subprocess
import sys
from concurrent.futures import TimeoutError
from pprint import pprint

import google.cloud.pubsub_v1 as pubsub

from gce_provider.config import get_config
from gce_provider.db.machines import MachineDao
from gce_provider.utils import client_factory
from gce_provider.utils.model_utils import to_simple_namespace
from gce_provider.utils.process_lock import LockManager, LockManagerError

# Documentation at https://cloud.google.com/pubsub/docs/publish-receive-messages-client-library


def callback(message: pubsub.subscriber.message.Message) -> None:
    config = get_config()
    logger = config.logger
    logger.debug(f"Received message:\n{pprint(message)}\n")

    try:
        data_bytes = message.data.decode("utf-8")
        data_json = json.loads(data_bytes)
        logger.debug(f"Message data:\n{json.dumps(data_json)}\n\n")
        message_obj = to_simple_namespace(data_json)
        hf_callback = MachineDao(config).update_machine_state(message_obj)

        message.ack()
        if hf_callback is not None:
            logger.info(f"Invoking HF callback {hf_callback}")
            hf_callback(message_obj)
            logger.info(f"HF Callback {hf_callback} completed.")
    except Exception as e:
        logger.error("Error handling HF callback", e)

    return


def launch_pubsub_daemon():
    """Launch pubsub as a process within Python"""
    config = get_config()
    logger = config.logger
    logger.info("Launching or refreshing pubsub daemon")
    logger.debug(f"pubsub process: {__file__}")
    subprocess.Popen(
        [sys.executable, __file__],
        start_new_session=True,
        # avoid any shared resources with the parent
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )


def main():
    config = get_config()
    logger = config.logger

    # If we are auto-launching, we can timeout the listener because HostFactory will repeatedly call the script.
    # If this script is being manually launched, we do not want to set up a timeout because the sys admin
    # will want to control this on their own.

    if not config.pubsub_auto_launch:
        pubsub_timeout = None
    else:
        pubsub_timeout = config.pubsub_timeout_seconds or None

    try:
        with LockManager(config.pubsub_lockfile):
            project_id = config.gcp_project_id or None
            subscription_id = config.pubsub_subscription

            subscriber = client_factory.pubsub_subscriber_client()
            # The `subscription_path` method creates a fully qualified identifier
            # in the form `projects/{project_id}/subscriptions/{subscription_id}`
            subscription_path = subscriber.subscription_path(
                project_id, subscription_id
            )

            streaming_pull_future = subscriber.subscribe(
                subscription_path, callback=callback
            )
            logger.info(f"Listening for messages on {subscription_path} ...\n")
            if pubsub_timeout:
                logger.info(f"Listener will timeout after {pubsub_timeout} seconds.\n")

            # Wrap subscriber in a 'with' block to automatically call close() when done.
            with subscriber:
                try:
                    streaming_pull_future.result(pubsub_timeout)
                except TimeoutError:
                    logger.info(
                        f"Pubsub timer reached timeout after {pubsub_timeout} seconds. Shutting down."
                    )
                    streaming_pull_future.cancel()  # Trigger the shutdown.
                    streaming_pull_future.result()  # Block until the shutdown is complete.
    except LockManagerError as e:
        logger.info(f"pubsub process exits: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
