import logging
import os
from functools import lru_cache

from dotenv import load_dotenv
from socket import gethostname

import common.utils.path_utils as path_utils
from common.utils.file_utils import load_json_file

# Load environment variables from .env file (if it exists)
load_dotenv()

# Allow for user to set the environment variable prefix if they desire
ENV_VAR_PREFIX = "GCP_HF_"

# Environment vars set by HostFactory
ENV_EGOSC_INSTANCE_HOST = "EGOSC_INSTANCE_HOST"
ENV_HF_DBDIR = "HF_DBDIR"
ENV_HF_PROVIDER_CONFDIR = "HF_PROVIDER_CONFDIR"
ENV_HF_PROVIDER_LOGDIR = "HF_PROVIDER_LOGDIR"
ENV_HF_PROVIDER_NAME = "HF_PROVIDER_NAME"


# Default configuration values
DEFAULT_LOG_LEVEL = "WARNING"
DEFAULT_INSTANCE_PREFIX = "sym-"
DEFAULT_HF_PROVIDER_NAME = "gcp-symphony"
DEFAULT_HF_TEMPLATES_FILENAME = "gcpgceinstprov_templates.json"
DEFAULT_CONFIG_FILENAME = "gcpgceinstprov_config.json"
DEFAULT_DB_FILENAME = DEFAULT_HF_PROVIDER_NAME
DEFAULT_GCP_CREDENTIALS_FILE = None
DEFAULT_PUBSUB_TIMEOUT_SECONDS = "0"
DEFAULT_PUBSUB_TOPIC = "hf-gce-vm-events"
DEFAULT_PUBSUB_LOCKFILE = "/tmp/sym_hf_gcp_pubsub.lock"
DEFAULT_PUBSUB_AUTOLAUNCH = False

CONFIG_VAR_HF_DBDIR = "HF_DBDIR"
CONFIG_VAR_HF_TEMPLATES_FILENAME = "HF_TEMPLATES_FILENAME"
CONFIG_VAR_GCP_CREDENTIALS_FILE = "GCP_CREDENTIALS_FILE"
CONFIG_VAR_GCP_PROJECT_ID = "GCP_PROJECT_ID"
CONFIG_VAR_GCP_INSTANCE_PREFIX = "GCP_INSTANCE_PREFIX"
CONFIG_VAR_LOGFILE = "LOGFILE"
CONFIG_VAR_LOG_LEVEL = "LOG_LEVEL"
CONFIG_VAR_PUBSUB_TIMEOUT_SECONDS = "PUBSUB_TIMEOUT"
CONFIG_VAR_PUBSUB_TOPIC = "PUBSUB_TOPIC"
CONFIG_VAR_PUBSUB_SUBSCRIPTION = "PUBSUB_SUBSCRIPTION"
CONFIG_VAR_PUBSUB_LOCKFILE = "PUBSUB_LOCKFILE"
CONFIG_VAR_PUBSUB_AUTOLAUNCH = "PUBSUB_AUTOLAUNCH"


def prepend_env_var(var: str) -> str:
    return f"{ENV_VAR_PREFIX}{var}"


# Environment vars to configure this plugin
ENV_PLUGIN_DB_FILENAME = prepend_env_var("DB_FILENAME")
ENV_PLUGIN_CONFIG_FILENAME = prepend_env_var("CONFIG_FILENAME")

HF_PROVIDER_NAME = os.environ.get(ENV_HF_PROVIDER_NAME, DEFAULT_HF_PROVIDER_NAME)
HF_PROVIDER_LOGDIR = os.environ.get(ENV_HF_PROVIDER_LOGDIR)
EGOSC_INSTANCE_HOST = os.environ.get(ENV_EGOSC_INSTANCE_HOST)
HF_PROVIDER_LOGFILE = (
    os.path.join(
        HF_PROVIDER_LOGDIR, f"{HF_PROVIDER_NAME}-provider.{EGOSC_INSTANCE_HOST}.log"
    )
    if HF_PROVIDER_LOGDIR
    else None
)

logging.getLogger(__name__)


class Config:
    """Configuration class for the application."""

    def __init__(self):
        """Check for required environment variables"""
        required_env_vars = [ENV_HF_PROVIDER_CONFDIR]
        missing_env_vars = list(
            filter(lambda x: os.environ.get(x) is None, required_env_vars)
        )
        if len(missing_env_vars) > 0:
            raise RuntimeError(
                (
                    f"Error: Please specify the environment variables {required_env_vars}. "
                    "If this script is being executed by HostFactory, the environment file "
                    "should have been configured. If executing outside of HostFactory, "
                    "you must manually set these variables in your environment"
                )
            )

        """Load configuration values from environment"""
        self.hf_provider_name = HF_PROVIDER_NAME
        self.hf_provider_conf_dir: str = os.environ.get(ENV_HF_PROVIDER_CONFDIR)

        """Load configuration values from provider config"""
        hf_provider_conf_path = os.path.join(
            self.hf_provider_conf_dir,
            os.environ.get(ENV_PLUGIN_CONFIG_FILENAME, DEFAULT_CONFIG_FILENAME),
        )

        hf_provider_conf = load_json_file(hf_provider_conf_path)
        if hf_provider_conf is None:
            raise Exception(
                f"Error: Please configure the plugin via the file {hf_provider_conf_path}"
            )

        # determine the instance label value text, defaulting to hostname
        self.instance_label_name_text = "symphony_gce_connector"
        try:
            self.instance_label_value_text = gethostname()  # type: ignore
        except Exception as e:
            self.logger.error(
                "Unable to get hostname via socket class."
                f" Will have to use the default.\n {e}"
            )
            self.instance_label_value_text = "KeepingUpWithTheGCEConnector"

        # configure general settings
        self.gcp_credentials_file = hf_provider_conf.get(
            CONFIG_VAR_GCP_CREDENTIALS_FILE, DEFAULT_GCP_CREDENTIALS_FILE
        )
        self.gcp_project_id = hf_provider_conf.get(CONFIG_VAR_GCP_PROJECT_ID)
        self.gcp_instance_prefix = hf_provider_conf.get(
            CONFIG_VAR_GCP_INSTANCE_PREFIX, DEFAULT_INSTANCE_PREFIX
        ).lower()
        self.hf_templates_filename = hf_provider_conf.get(
            CONFIG_VAR_HF_TEMPLATES_FILENAME, DEFAULT_HF_TEMPLATES_FILENAME
        )

        # configure DB
        self.hf_db_dir = hf_provider_conf.get(
            CONFIG_VAR_HF_DBDIR, os.environ.get(ENV_HF_DBDIR)
        )
        if self.hf_db_dir is None:
            raise RuntimeError(
                (
                    "Please specify the location of the database. This can be set by"
                    f" setting {CONFIG_VAR_HF_DBDIR} in the configuration file {hf_provider_conf_path}."
                    f" Alternatively, you can set the environment variable {ENV_HF_DBDIR}. Please be aware"
                    " that if you choose to set the environment variable, HostFactory must also be configured"
                    " to provide that value at runtime."
                )
            )

        self.db_name = os.environ.get(ENV_PLUGIN_DB_FILENAME, DEFAULT_DB_FILENAME)
        self.db_path = path_utils.normalize_path(self.hf_db_dir, self.db_name)

        # configure pubsub
        self.pubsub_timeout_seconds = int(
            hf_provider_conf.get(
                CONFIG_VAR_PUBSUB_TIMEOUT_SECONDS, DEFAULT_PUBSUB_TIMEOUT_SECONDS
            )
        )
        self.pubsub_topic = hf_provider_conf.get(
            CONFIG_VAR_PUBSUB_TOPIC, DEFAULT_PUBSUB_TOPIC
        )
        self.pubsub_subscription = (
            hf_provider_conf.get(CONFIG_VAR_PUBSUB_SUBSCRIPTION)
            or f"{self.pubsub_topic}-sub"
        )

        self.pubsub_lockfile = hf_provider_conf.get(
            CONFIG_VAR_PUBSUB_LOCKFILE, DEFAULT_PUBSUB_LOCKFILE
        )

        self.pubsub_auto_launch: bool = bool(
            hf_provider_conf.get(
                CONFIG_VAR_PUBSUB_AUTOLAUNCH, DEFAULT_PUBSUB_AUTOLAUNCH
            )
        )

        # configure logging
        self.hf_provider_log_file = hf_provider_conf.get(
            CONFIG_VAR_LOGFILE, HF_PROVIDER_LOGFILE
        )
        self.log_level = hf_provider_conf.get(CONFIG_VAR_LOG_LEVEL, DEFAULT_LOG_LEVEL)

        logging.basicConfig(
            format="%(asctime)s - %(levelname)s - %(message)s",
            filename=self.hf_provider_log_file,
            level=self.log_level.upper() if self.log_level else DEFAULT_LOG_LEVEL,
        )
        self.logger = logging.getLogger(__name__)

        # iterate over the class attributes and log them
        if self.log_level.upper() == "DEBUG":
            self.logger.debug("Configuration loaded:")
            for attr in dir(self):
                if not attr.startswith("_") and not callable(getattr(self, attr)):
                    self.logger.debug(f"  {attr}: {getattr(self, attr)}")
        else:
            self.logger.info("Configuration loaded.")
        self.__initialized = True


@lru_cache(maxsize=1)
def get_config() -> Config:
    return Config()
