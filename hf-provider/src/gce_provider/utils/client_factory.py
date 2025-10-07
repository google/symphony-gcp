import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

import google.cloud.compute_v1 as compute
import google.cloud.pubsub_v1 as pubsub
from google.oauth2 import service_account

from common.utils.file_utils import load_json_file
from common.utils.path_utils import normalize_path
from gce_provider.config import Config, get_config


@lru_cache(maxsize=1)
def get_credentials(
    config: Optional[Config] = None,
) -> Optional[service_account.Credentials]:
    if config is None:
        config = get_config()

    if config.gcp_credentials_file and Path.exists(config.gcp_credentials_file):
        credentials_file_path = normalize_path(
            config.hf_provider_conf_dir, config.gcp_credentials_file
        )

        try:
            credentials_json = load_json_file(credentials_file_path)
            return service_account.Credentials.from_service_account_info(
                credentials_json
            )
        except Exception:
            config.logger.error(
                f"Unable to create service account credentials from file {credentials_file_path}"
            )

    logging.warning(
        "No credentials file defined, or file does not exist. Will rely on application default credentials."
    )
    return None


@lru_cache(maxsize=1)
def instances_client(config: Optional[Config] = None):
    return compute.InstancesClient(credentials=get_credentials(config))


@lru_cache(maxsize=1)
def instance_groups_client(config: Optional[Config] = None):
    return compute.InstanceGroupsClient(credentials=get_credentials(config))


@lru_cache(maxsize=1)
def instance_group_managers_client(config: Optional[Config] = None):
    return compute.InstanceGroupManagersClient(credentials=get_credentials(config))


@lru_cache(maxsize=1)
def pubsub_subscriber_client(config: Optional[Config] = None):
    return pubsub.SubscriberClient(credentials=get_credentials(config))
