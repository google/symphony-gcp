import logging
import os
from functools import lru_cache
from socket import gethostname

from dotenv import load_dotenv

import common.utils.path_utils as path_utils
from common.utils.file_utils import load_json_file

# Load environment variables from .env file (if it exists)
load_dotenv()

# Allow for user to set the environment variable prefix if they desire
ENV_VAR_PREFIX = "GCP_HF_"

# Default configuration values
DEFAULT_PORT = 8080
DEFAULT_NAMESPACE = "gcp-symphony"
DEFAULT_CRD_GROUP = "accenture.com"
DEFAULT_CRD_VERSION = "v1"
DEFAULT_CRD_KIND = "GCPSymphonyResource"
DEFAULT_CRD_SINGULAR = "gcp-symphony-resource"
DEFAULT_CRD_PLURAL = f"{DEFAULT_CRD_SINGULAR}s"
DEFAULT_CRD_RETURN_REQUEST_SINGULAR = "machine-return-request"
DEFAULT_CRD_RETURN_REQUEST_PLURAL = f"{DEFAULT_CRD_RETURN_REQUEST_SINGULAR}s"
DEFAULT_CRD_RETURN_REQUEST_KIND = "MachineReturnRequest"
DEFAULT_REQUEST_TIMEOUT = 300
DEFAULT_POLLING_INTERVAL = 10
DEFAULT_FAST_API_ENABLED = False
DEFAULT_LOG_LEVEL = "WARNING"

DEFAULT_HF_PROVIDER_NAME = "gcp-symphony"

HF_PROVIDER_NAME = os.environ.get("HF_PROVIDER_NAME", DEFAULT_HF_PROVIDER_NAME)
HF_PROVIDER_CONFDIR_ENV = "HF_PROVIDER_CONFDIR"
HF_PROVIDER_LOGDIR = os.environ.get("HF_PROVIDER_LOGDIR")
EGOSC_INSTANCE_HOST = os.environ.get("EGOSC_INSTANCE_HOST")
HF_PROVIDER_LOGFILE = (
    os.path.join(HF_PROVIDER_LOGDIR, f"{HF_PROVIDER_NAME}-provider.{EGOSC_INSTANCE_HOST}.log")
    if HF_PROVIDER_LOGDIR
    else None
)

logging.getLogger(__name__)

PROVIDER_CONF_GKE_KUBECONFIG = "GKE_KUBECONFIG"
KUBECONFIG_DEFAULT_ENV = "KUBECONFIG"


class Config:
    """Configuration class for the application."""

    def __init__(self) -> None:
        """Load configuration values from environment"""
        self.hf_provider_name = HF_PROVIDER_NAME

        self.hf_provider_conf_dir: str = os.environ.get(HF_PROVIDER_CONFDIR_ENV, "")

        if not self.hf_provider_conf_dir:
            raise RuntimeError(
                (
                    f"Error: Please specify the environment variable {HF_PROVIDER_CONFDIR_ENV}. "
                    "If this script is being executed by HostFactory, the environment file should "
                    "have been configured. If executing outside of HostFactory, you must provide "
                    "this variable in your environment, e.g. "
                    f"{HF_PROVIDER_CONFDIR_ENV}="
                    "/opt/ibm/spectrumcomputing/hostfactory/conf/providers/gcpgkeinst/"
                )
            )

        """Load configuration values from provider config"""
        hf_provider_conf_path = os.path.join(
            self.hf_provider_conf_dir, "gcpgkeinstprov_config.json"
        )

        hf_provider_conf = load_json_file(hf_provider_conf_path)
        if hf_provider_conf is None:
            raise Exception(
                f"Error: Please configure the plugin via the file {hf_provider_conf_path}"
            )

        self.env_var_prefix = os.environ.get(f"{ENV_VAR_PREFIX}ENV_VAR_PREFIX", ENV_VAR_PREFIX)

        # determine the kubeconfig path from the provider configuation,
        # falling back to default env variable
        kube_config_path = hf_provider_conf.get(PROVIDER_CONF_GKE_KUBECONFIG)
        if kube_config_path is not None:
            kube_config_path = path_utils.normalize_path(
                self.hf_provider_conf_dir, kube_config_path
            )
        else:
            kube_config_path = os.environ.get(KUBECONFIG_DEFAULT_ENV)

        if kube_config_path is not None:
            self.kube_config = kube_config_path
        else:
            raise Exception(
                (
                    "Please specify the Kubernetes configuration file either by setting the "
                    "configuration parameter {PROVIDER_CONF_GKE_KUBECONFIG} in "
                    f"{hf_provider_conf_path}, or by setting the default environment "
                    "variable {KUBECONFIG_DEFAULT_ENV}."
                )
            )

        self.crd_namespace = hf_provider_conf.get("GKE_CRD_NAMESPACE", DEFAULT_NAMESPACE)
        self.crd_group = hf_provider_conf.get("GKE_CRD_GROUP", DEFAULT_CRD_GROUP)
        self.crd_version = hf_provider_conf.get("GKE_CRD_VERSION", DEFAULT_CRD_VERSION)
        self.crd_kind = hf_provider_conf.get("GKE_CRD_KIND", DEFAULT_CRD_KIND)
        self.crd_singular = hf_provider_conf.get("GKE_CRD_SINGULAR", DEFAULT_CRD_SINGULAR)
        self.crd_plural = hf_provider_conf.get("GKE_CRD_PLURAL", f"{self.crd_singular}s")
        self.crd_label_name_text = "symphony_gke_connector"
        # Get the hostname from the running environment for use in the crd_label_value_text
        try:
            self.crd_label_value_text = gethostname()  # type: ignore
        except Exception as e:
            self.crd_label_value_text = "KeepingUpWithTheGKEConnector"
        self.crd_return_request_singular = hf_provider_conf.get(
            "GKE_CRD_RETURN_REQUEST_SINGULAR", DEFAULT_CRD_RETURN_REQUEST_SINGULAR
        )
        self.crd_return_request_plural = f"{self.crd_return_request_singular}s"
        self.crd_return_request_kind = hf_provider_conf.get(
            "GKE_CRD_RETURN_REQUEST_KIND", DEFAULT_CRD_RETURN_REQUEST_KIND
        )
        self.request_timeout = int(
            hf_provider_conf.get("GKE_REQUEST_TIMEOUT", DEFAULT_REQUEST_TIMEOUT)
        )
        self.polling_interval = int(
            hf_provider_conf.get("GKE_POLLING_INTERVAL", DEFAULT_POLLING_INTERVAL)
        )
        # This allows the user to override the default HF log directory/filename
        self.hf_provider_log_file = hf_provider_conf.get("LOGFILE", HF_PROVIDER_LOGFILE)
        self.log_level = hf_provider_conf.get("LOG_LEVEL", DEFAULT_LOG_LEVEL)

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
