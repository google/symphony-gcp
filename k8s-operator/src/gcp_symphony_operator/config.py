import asyncio
import enum
import json
import logging
import os
from datetime import datetime, timezone
from typing import List, Optional

from typing_extensions import Self

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s")


class LogFormatters(str, enum.Enum):
    """
    Enum for log formatters.
    This is used to allow for different log formats to be used in the future.
    """

    STRUCTURED = "structured"
    """
    Use structured logging format.
    """

    SIMPLE = "simple"
    """
    Use simple logging format.
    """


class Config:
    """
    Configuration class for the GCP Symphony Operator.
    """

    # Allow for user to set the environment variable prefix if they desire
    ENV_VAR_PREFIX = "GCP_HF_"
    """
    str: A prefix for all other environment variables. Used to allow for multiple configurations.
    Default is "GCP_HF_".
    """

    DEFAULT_NAMESPACES = ["gcp-symphony"]
    """
    list[str]: A list of strings respresenting the namespaces to be monitored by the opoerator.
    The operator will only monitor the first namespace at the moment.
    A future version may make use of additional namespaces in the list.
    Default is ["gcp-symphony"].
    """

    DEFAULT_OPERATOR_NAME = "gcp-symphony-operator"
    DEFAULT_OPERATOR_IMAGE_TAG = "latest"
    DEFAULT_KUBECONFIG_PATH = "/app/.kube/config"
    DEFAULT_CONTAINER_IMAGE = "nginx:latest"  # fallback value used for testing only
    DEFAULT_KUBERNETES_RBAC_CHECK = False

    DEFAULT_KUBERNETES_CLIENT_TIMEOUT_ENABLE = False
    """
    bool: Whether to enable the Kubernetes client timeout.
    """

    DEFAULT_KUBERNETES_CLIENT_TIMEOUT = 10
    """
    int: The timeout in seconds for Kubernetes client requests.
    """

    DEFAULT_ENABLE_GKE_PREEMPTION_HANDLING = True
    """
    bool: Whether to enable GKE preemption handling.
    This will allow the operator to handle GKE Spot VM preemption events.
    The behavior is to create a MachineReturnRequest custom resource and allow
    for the operator to delete the affected pods and track them appropriately
    on their parent GCPSymphonyResource
    Default is True.
    """

    DEFAULT_KOPF_POSTING_ENABLED = False
    """
    bool: Whether to enable kopf posting. This places kopf event logging on
    the custom resource status. This can cause sever bloating on the custom
    resource and is not recommended outside of a development or integration
    testing environment.
    Default is False.
    """
    DEFAULT_KOPF_SERVER_TIMEOUT = 300
    """int: Value to set for the kopf.watching.server_timeout setting."""

    DEFAULT_KOPF_MAX_WORKERS = 20
    """int: The maximum number of workers that kopf can use.
       This sets the kopf."""

    DEFAULT_MIN_REQUEST_ID_LENGTH = 8
    DEFAULT_REQUEST_ID_INTERNAL_PREFIX = "int-"
    DEFAULT_PREEMPTED_MACHINE_REQUEST_ID_PREFIX = "prmt-"

    DEFAULT_LOG_FILE = "gcp-symphony-operator.log"
    DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    DEFAULT_LOG_LEVEL = "INFO"
    DEFAULT_LOG_FORMATTER = LogFormatters.STRUCTURED

    DEFAULT_MANIFEST_BASE_PATH = "manifests"
    """
    str: The base path for all manifests used by the operator.
    leave this empty to use the manifests in the codebase below
    """
    DEFAULT_RBAC_PATH = f"{DEFAULT_MANIFEST_BASE_PATH}/rbac"
    DEFAULT_SERVICE_ACCOUNT_FILE = "operator-sa.yaml.j2"
    DEFAULT_CLUSTER_ROLE_FILE = "operator-clusterrole.yaml.j2"
    DEFAULT_CLUSTER_ROLE_BINDING_FILE = "operator-clusterrole-binding.yaml.j2"
    DEFAULT_NAMESPACE_ROLE_FILE = "operator-role.yaml.j2"
    DEFAULT_NAMESPACE_ROLE_BINDING_FILE = "operator-role-binding.yaml.j2"

    DEFAULT_SERVICE_ACCOUNT_NAME = f"{DEFAULT_OPERATOR_NAME}-sa"
    DEFAULT_NAMESPACE_ROLE_NAME = f"{DEFAULT_OPERATOR_NAME}-role"
    DEFAULT_NAMESPACE_ROLE_BINDING_NAME = f"{DEFAULT_OPERATOR_NAME}-role-binding"
    DEFAULT_NAMESPACE_MANIFEST_FILE = "namespace.yaml.j2"

    DEFAULT_CLUSTER_ROLE_NAME = f"{DEFAULT_OPERATOR_NAME}-cluster-role"
    DEFAULT_CLUSTER_ROLE_BINDING_NAME = f"{DEFAULT_OPERATOR_NAME}-cluster-role-binding"

    DEFAULT_CRD_MANIFEST_PATH = f"{DEFAULT_MANIFEST_BASE_PATH}/crd"
    DEFAULT_CRD_MANIFEST_FILE = "gcp-symphony-crd.yaml.j2"
    DEFAULT_CRD_DELETE_REQUEST_MANIFEST_FILE = "return-request-crd.yaml.j2"
    DEFAULT_CRD_UPDATE_RETRY_COUNT = 3
    DEFAULT_CRD_UPDATE_RETRY_INTERVAL = 0.5
    DEFAULT_CRD_UPDATE_BATCH_SIZE = 50

    DEFAULT_CRD_KIND = "GCPSymphonyResource"
    DEFAULT_CRD_SHORT_NAME = "gcpsr"
    DEFAULT_CRD_GROUP = "accenture.com"
    DEFAULT_CRD_SINGULAR = "gcp-symphony-resource"
    DEFAULT_CRD_API_VERSION = "v1"
    DEFAULT_CRD_FINALIZER = "symphony-operator/finalizer"
    DEFAULT_CRD_RETURN_REQUEST_SINGULAR = "machine-return-request"
    DEFAULT_CRD_RETURN_REQUEST_PLURAL = f"{DEFAULT_CRD_RETURN_REQUEST_SINGULAR}s"
    DEFAULT_CRD_RETURN_REQUEST_SHORT_NAME = "rrm"
    DEFAULT_CRD_RETURN_REQUEST_KIND = "MachineReturnRequest"
    DEFAULT_CRD_DELETED_PODS_MAXIMUM = (
        0  # don't limit the number of deleted pods on the list
    )
    DEFAULT_CRD_COMPLETED_RETAIN_TIME = 1440  # in minutes. 24 hours
    """
    int: The time in minutes to retain complete custom resources before deleting them.
    Default is 120.
    """
    DEFAULT_CRD_COMPLETED_CHECK_INTERVAL = 30
    """
    int: The interval in minutes to check for completed custome resrouces and manage accordingly.
    Default is 30.
    """

    DEFAULT_MINIMUM_MACHINE_COUNT = 1
    DEFAULT_MAXIMUM_MACHINE_COUNT = 1000  # use 0 for no maximum
    DEFAULT_POD_CREATION_BATCH_SIZE = 10  # Number of pods to create in a batch
    DEFAULT_POD_CONTAINER_PORT = 8080
    DEFAULT_POD_GRACE_PERIOD = 30
    DEFAULT_POD_SYSTEM_INITIATED_RETURN_MSG = "system-initiated-return"

    # Health check configuration
    DEFAULT_HEALTH_CHECK_ENABLED = True
    DEFAULT_HEALTH_CHECK_PORT = 8080
    DEFAULT_HEALTH_CHECK_PATH = "/health"
    DEFAULT_READINESS_CHECK_PATH = "/ready"

    _instance: Optional["Config"] = None
    __initialized = False
    _thin: bool = False  # True indicates we don't need to load kubernetes config
    _k8s_config_loaded: bool = False

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.__initialized = False
        return cls._instance  # type: ignore

    async def __ainit__(self) -> None:
        if self.__initialized:
            return

        self.env_var_prefix = os.environ.get("ENV_VAR_PREFIX", Config.ENV_VAR_PREFIX)
        self.log_level = os.environ.get(
            f"{self.env_var_prefix}LOG_LEVEL", Config.DEFAULT_LOG_LEVEL
        ).upper()
        self.log_format = os.environ.get(
            f"{self.env_var_prefix}LOG_FORMAT", Config.DEFAULT_LOG_FORMAT
        )
        self.log_file = os.environ.get(
            f"{self.env_var_prefix}LOG_FILE", Config.DEFAULT_LOG_FILE
        )

        # Configure structured logging for cloud providers
        class StructuredFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                    "severity": record.levelname,
                    "message": record.getMessage(),
                    "logger": record.name,
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno,
                }
                if hasattr(record, "request_id"):
                    log_entry["request_id"] = record.request_id  # type: ignore
                if hasattr(record, "resource_name"):
                    log_entry["resource_name"] = record.resource_name  # type: ignore
                return json.dumps(log_entry)

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(self.log_level)

        self.log_formatter = os.environ.get(
            f"{self.env_var_prefix}LOG_FORMATTER", Config.DEFAULT_LOG_FORMATTER
        ).lower()
        if self.log_formatter == LogFormatters.STRUCTURED:
            # Remove existing handlers and add structured handler
            for handler in self.logger.handlers[:]:
                self.logger.removeHandler(handler)

            handler = logging.StreamHandler()
            handler.setFormatter(StructuredFormatter())
            self.logger.addHandler(handler)
            self.logger.propagate = False

            # Configure kopf and kubernetes loggers with structured format
            for logger_name in ["kopf", "kubernetes", "urllib3"]:
                ext_logger = logging.getLogger(logger_name)
                ext_logger.handlers.clear()
                ext_handler = logging.StreamHandler()
                ext_handler.setFormatter(StructuredFormatter())
                ext_logger.addHandler(ext_handler)
                ext_logger.propagate = False
                ext_logger.setLevel(self.log_level)

        self.manifest_base_path = os.environ.get(
            f"{self.env_var_prefix}MANIFEST_BASE_PATH",
            Config.DEFAULT_MANIFEST_BASE_PATH,
        )
        self.default_namespaces = self._get_default_namespaces()
        kubernetes_rbac_check_str = os.environ.get(
            f"{self.env_var_prefix}KUBERNETES_RBAC_CHECK",
            str(Config.DEFAULT_KUBERNETES_RBAC_CHECK),
        ).lower()
        self.kubernetes_rbac_check = kubernetes_rbac_check_str in ("true", "1", "yes")
        kubernetes_client_timeout_enable_str = os.getenv(
            f"{self.env_var_prefix}KUBERNETES_CLIENT_TIMEOUT_ENABLE",
            str(Config.DEFAULT_KUBERNETES_CLIENT_TIMEOUT_ENABLE),
        )
        self.kubernetes_client_timeout_enable = (
            kubernetes_client_timeout_enable_str.lower() in ("true", "1", "yes")
        )
        self.kubernetes_client_timeout = (
            int(
                os.environ.get(
                    f"{self.env_var_prefix}KUBERNETES_CLIENT_TIMEOUT",
                    Config.DEFAULT_KUBERNETES_CLIENT_TIMEOUT,
                )
            )
            if self.kubernetes_client_timeout_enable
            else None
        )
        self.enable_gke_preemption_handling = os.environ.get(
            f"{self.env_var_prefix}ENABLE_GKE_PREEMPTION_HANDLING",
            str(Config.DEFAULT_ENABLE_GKE_PREEMPTION_HANDLING),
        ).lower() in ("true", "1", "yes")
        self.kubeconfig_path = os.environ.get(
            f"{self.env_var_prefix}KUBECONFIG_PATH", Config.DEFAULT_KUBECONFIG_PATH
        )
        self.kubernetes_client_log_level = os.environ.get(
            f"{self.env_var_prefix}KUBERNETES_CLIENT_LOG_LEVEL",
            Config.DEFAULT_LOG_LEVEL,
        ).upper()
        self.cluster_role_name = os.environ.get(
            f"{self.env_var_prefix}CLUSTER_ROLE_NAME", Config.DEFAULT_CLUSTER_ROLE_NAME
        )
        self.cluster_role_binding_name = os.environ.get(
            f"{self.env_var_prefix}CLUSTER_ROLE_BINDING_NAME",
            Config.DEFAULT_CLUSTER_ROLE_BINDING_NAME,
        )
        self.namespace_role_name = os.environ.get(
            f"{self.env_var_prefix}NAMESPACE_ROLE_NAME",
            Config.DEFAULT_NAMESPACE_ROLE_NAME,
        )
        self.namespace_role_binding_name = os.environ.get(
            f"{self.env_var_prefix}NAMESPACE_ROLE_BINDING_NAME",
            Config.DEFAULT_NAMESPACE_ROLE_BINDING_NAME,
        )
        self.service_account_name = os.environ.get(
            f"{self.env_var_prefix}SERVICE_ACCOUNT_NAME",
            Config.DEFAULT_SERVICE_ACCOUNT_NAME,
        )
        self.min_request_id_length = int(
            os.environ.get(
                f"{self.env_var_prefix}MIN_REQUEST_ID_LENGTH",
                Config.DEFAULT_MIN_REQUEST_ID_LENGTH,
            )
        )
        self.request_id_internal_prefix = os.environ.get(
            f"{self.env_var_prefix}REQUEST_ID_INTERNAL_PREFIX",
            Config.DEFAULT_REQUEST_ID_INTERNAL_PREFIX,
        )
        self.preempted_machine_request_id_prefix = os.environ.get(
            f"{self.env_var_prefix}PREEMPTED_MACHINE_REQUEST_ID_PREFIX",
            Config.DEFAULT_PREEMPTED_MACHINE_REQUEST_ID_PREFIX,
        )
        self.operator_name = os.environ.get(
            f"{self.env_var_prefix}OPERATOR_NAME", Config.DEFAULT_OPERATOR_NAME
        )
        self.operator_image_tag = os.environ.get(
            f"{self.env_var_prefix}OPERATOR_IMAGE_TAG",
            Config.DEFAULT_OPERATOR_IMAGE_TAG,
        )
        self.operator_manifest_file = os.environ.get(
            f"{self.env_var_prefix}OPERATOR_MANIFEST_FILE",
            f"{self.operator_name}.yaml.j2",
        )
        self.base_manifest_path = os.environ.get(
            f"{self.env_var_prefix}MANIFEST_BASE_PATH",
            Config.DEFAULT_MANIFEST_BASE_PATH,
        )
        self.service_account_file = os.environ.get(
            f"{self.env_var_prefix}SERVICE_ACCOUNT_FILE",
            Config.DEFAULT_SERVICE_ACCOUNT_FILE,
        )
        self.rbac_manifest_path = os.environ.get(
            f"{self.env_var_prefix}RBAC_PATH", f"{self.base_manifest_path}/rbac"
        )
        self.namespace_manifest_path = os.environ.get(
            f"{self.env_var_prefix}NAMESPACE_MANIFEST_PATH",
            f"{self.base_manifest_path}/namespace",
        )
        self.namespace_manifest_file = os.environ.get(
            f"{self.env_var_prefix}NAMESPACE_MANIFEST_FILE",
            Config.DEFAULT_NAMESPACE_MANIFEST_FILE,
        )
        self.cluster_role_file = os.environ.get(
            f"{self.env_var_prefix}CLUSTER_ROLE_FILE", Config.DEFAULT_CLUSTER_ROLE_FILE
        )
        self.cluster_role_binding_file = os.environ.get(
            f"{self.env_var_prefix}CLUSTER_ROLE_BINDING_FILE",
            Config.DEFAULT_CLUSTER_ROLE_BINDING_FILE,
        )
        self.namespace_role_file = os.environ.get(
            f"{self.env_var_prefix}RBAC_ROLE_FILE", Config.DEFAULT_NAMESPACE_ROLE_FILE
        )
        self.namespace_role_binding_file = os.environ.get(
            f"{self.env_var_prefix}RBAC_ROLE_BINDING_FILE",
            Config.DEFAULT_NAMESPACE_ROLE_BINDING_FILE,
        )
        self.crd_manifest_path = os.environ.get(
            f"{self.env_var_prefix}CRD_MANIFEST_PATH", Config.DEFAULT_CRD_MANIFEST_PATH
        )
        self.crd_manifest_file = os.environ.get(
            f"{self.env_var_prefix}CRD_MANIFEST_FILE", Config.DEFAULT_CRD_MANIFEST_FILE
        )
        self.crd_return_request_manifest_file = os.environ.get(
            f"{self.env_var_prefix}CRD_RETURN_REQUEST_MANIFEST_FILE",
            Config.DEFAULT_CRD_DELETE_REQUEST_MANIFEST_FILE,
        )
        self.crd_kind = os.environ.get(
            f"{self.env_var_prefix}CRD_KIND", Config.DEFAULT_CRD_KIND
        )
        self.crd_short_name = os.environ.get(
            f"{self.env_var_prefix}CRD_SHORT_NAME", Config.DEFAULT_CRD_SHORT_NAME
        )
        self.crd_singular = os.environ.get(
            f"{self.env_var_prefix}CRD_SINGULAR", Config.DEFAULT_CRD_SINGULAR
        )
        self.crd_plural = f"{self.crd_singular}s"
        self.crd_return_request_singular = os.environ.get(
            f"{self.env_var_prefix}CRD_RETURN_REQUEST_SINGULAR",
            Config.DEFAULT_CRD_RETURN_REQUEST_SINGULAR,
        )
        self.crd_return_request_plural = f"{self.crd_return_request_singular}s"
        self.crd_return_request_kind = os.environ.get(
            f"{self.env_var_prefix}CRD_RETURN_REQUEST_KIND",
            Config.DEFAULT_CRD_RETURN_REQUEST_KIND,
        )
        self.crd_return_request_short_name = os.environ.get(
            f"{self.env_var_prefix}CRD_RETURN_REQUEST_SHORT_NAME",
            Config.DEFAULT_CRD_RETURN_REQUEST_SHORT_NAME,
        )
        self.crd_group = os.environ.get(
            f"{self.env_var_prefix}CRD_GROUP", Config.DEFAULT_CRD_GROUP
        )
        self.crd_api_version = os.environ.get(
            f"{self.env_var_prefix}CRD_API_VERSION", Config.DEFAULT_CRD_API_VERSION
        )
        self.crd_update_retry_count = int(
            os.environ.get(
                f"{self.env_var_prefix}CRD_UPDATE_RETRY_COUNT",
                Config.DEFAULT_CRD_UPDATE_RETRY_COUNT,
            )
        )
        self.crd_update_retry_interval = float(
            os.environ.get(
                f"{self.env_var_prefix}CRD_UPDATE_RETRY_INTERVAL",
                Config.DEFAULT_CRD_UPDATE_RETRY_INTERVAL,
            )
        )
        self.crd_update_batch_size = int(
            os.environ.get(
                f"{self.env_var_prefix}CRD_UPDATE_BATCH_SIZE",
                Config.DEFAULT_CRD_UPDATE_BATCH_SIZE,
            )
        )

        # Get the CRD completed retain time value
        try:
            retain_time = os.environ.get(
                f"{self.env_var_prefix}CRD_COMPLETED_RETAIN_TIME",
                Config.DEFAULT_CRD_COMPLETED_RETAIN_TIME,
            )
            self.crd_completed_retain_time = self._parse_time_value(value=retain_time)
        except ValueError:
            self.logger.error(
                "Invalid CRD retain time value. Using default: "
                f"{Config.DEFAULT_CRD_COMPLETED_RETAIN_TIME} minutes."
            )
            self.crd_completed_retain_time = Config.DEFAULT_CRD_COMPLETED_RETAIN_TIME

        # Get the check interval value
        try:
            self.crd_completed_check_interval = int(
                os.environ.get(
                    f"{self.env_var_prefix}CRD_COMPLETED_CHECK_INTERVAL",
                    Config.DEFAULT_CRD_COMPLETED_CHECK_INTERVAL,
                )
            )
        except ValueError:
            self.logger.error(
                "Invalid CRD check interval value. Using default: "
                f"{Config.DEFAULT_CRD_COMPLETED_CHECK_INTERVAL} minutes."
            )
            self.crd_completed_check_interval = (
                Config.DEFAULT_CRD_COMPLETED_CHECK_INTERVAL
            )
        # Ensure check interval is less than retain time
        if self.crd_completed_check_interval >= self.crd_completed_retain_time:
            self.logger.warning(
                f"CRD check interval ({self.crd_completed_check_interval}) "
                f"must be less than retain time ({self.crd_completed_retain_time}). "
                f"Setting to {self.crd_completed_retain_time // 2} minutes."
            )
            self.crd_completed_check_interval = self.crd_completed_retain_time // 2
        self.crd_finalizer = os.environ.get(
            f"{self.env_var_prefix}CRD_FINALIZER", Config.DEFAULT_CRD_FINALIZER
        )
        self.crd_deleted_pods_maximum = os.environ.get(
            f"{self.env_var_prefix}CRD_DELETED_PODS_MAXIMUM",
            Config.DEFAULT_CRD_DELETED_PODS_MAXIMUM,
        )
        self.kopf_posting_enabled = os.environ.get(
            f"{self.env_var_prefix}KOPF_POSTING_ENABLED",
            str(Config.DEFAULT_KOPF_POSTING_ENABLED),
        ).lower() in ("true", "1", "yes")
        kopf_server_timeout_str = os.environ.get(
            f"{self.env_var_prefix}KOPF_SERVER_TIMEOUT",
            str(self.DEFAULT_KOPF_SERVER_TIMEOUT),
        )
        self.kopf_server_timeout = int(
            kopf_server_timeout_str
            if kopf_server_timeout_str.isdigit()
            else self.DEFAULT_KOPF_SERVER_TIMEOUT
        )
        kopf_max_workers_str = os.environ.get(
            f"{self.env_var_prefix}KOPF_MAX_WORKERS", str(self.DEFAULT_KOPF_MAX_WORKERS)
        )
        self.kopf_max_workers = int(
            kopf_max_workers_str
            if kopf_max_workers_str.isdigit()
            else self.DEFAULT_KOPF_MAX_WORKERS
        )

        self.pod_create_batch_size = int(
            os.environ.get(
                f"{self.env_var_prefix}POD_CREATE_BATCH_SIZE",
                Config.DEFAULT_POD_CREATION_BATCH_SIZE,
            )
        )
        self.pod_container_port = os.environ.get(
            f"{self.env_var_prefix}POD_CONTAINER_PORT",
            Config.DEFAULT_POD_CONTAINER_PORT,
        )
        self.default_pod_grace_period = int(
            os.environ.get(
                f"{self.env_var_prefix}POD_GRACE_PERIOD",
                Config.DEFAULT_POD_GRACE_PERIOD,
            )
        )
        self.system_initiated_return_msg = os.environ.get(
            f"{self.env_var_prefix}SYSTEM_INITIATED_RETURN_MSG",
            Config.DEFAULT_POD_SYSTEM_INITIATED_RETURN_MSG,
        )
        self.operator_pod_name = os.environ.get("POD_NAME", "unset")
        self.operator_pod_namespace = os.environ.get("POD_NAMESPACE", "unset")

        # Get the operator version from __init__.py if available
        try:
            from .__init__ import __version__

            self.operator_version = __version__
        except Exception as e:
            self.operator_version = "whiskey.tango.hotel"
            self.logger.warning(
                f"Error reading operator version from package metadata: {e}"
            )

        self.default_container_image = os.environ.get(
            f"{self.env_var_prefix}DEFAULT_CONTAINER_IMAGE",
            Config.DEFAULT_CONTAINER_IMAGE,
        )
        self.default_container_image_pull_policy = os.environ.get(
            f"{self.env_var_prefix}IMAGE_PULL_POLICY", "IfNotPresent"
        )
        self.default_minimum_machine_count = int(
            os.environ.get(
                f"{self.env_var_prefix}MINIMUM_MACHINE_COUNT",
                Config.DEFAULT_MINIMUM_MACHINE_COUNT,
            )
        )
        self.default_maximum_machine_count = int(
            os.environ.get(
                f"{self.env_var_prefix}MAXIMUM_MACHINE_COUNT",
                Config.DEFAULT_MAXIMUM_MACHINE_COUNT,
            )
        )

        # Health check configuration
        self.health_check_enabled = os.environ.get(
            f"{self.env_var_prefix}HEALTH_CHECK_ENABLED",
            str(Config.DEFAULT_HEALTH_CHECK_ENABLED),
        ).lower() in ("true", "1", "yes")
        self.health_check_port = int(
            os.environ.get(
                f"{self.env_var_prefix}HEALTH_CHECK_PORT",
                Config.DEFAULT_HEALTH_CHECK_PORT,
            )
        )
        self.health_check_path = os.environ.get(
            f"{self.env_var_prefix}HEALTH_CHECK_PATH",
            Config.DEFAULT_HEALTH_CHECK_PATH,
        )
        self.readiness_check_path = os.environ.get(
            f"{self.env_var_prefix}READINESS_CHECK_PATH",
            Config.DEFAULT_READINESS_CHECK_PATH,
        )

        if self.log_level == "DEBUG":
            # iterate over all config class attributes and log them
            for attr_name in dir(self):
                if not attr_name.startswith("_") and not callable(
                    getattr(self, attr_name)
                ):
                    self.logger.debug(f"{attr_name}: {getattr(self, attr_name)}")

        self.crd_plural_map = {
            self.crd_kind: self.crd_plural,
            self.crd_return_request_kind: self.crd_return_request_plural,
        }

        self.__initialized = True

        self.logger.debug("Config: Configuration initialized successfully.")

    def _get_default_namespaces(self) -> List[str]:
        namespaces = os.environ.get(
            f"{self.env_var_prefix}DEFAULT_NAMESPACES", self.DEFAULT_NAMESPACES
        )
        if isinstance(namespaces, str):
            namespaces = [namespaces]
        return namespaces

    def _get_crd_completed_check_interval(self) -> int:
        """
        Gets the CRD check interval from the environment, ensuring it's an integer.
        """
        interval_str = os.environ.get(
            f"{self.env_var_prefix}CRD_COMPLETED_CHECK_INTERVAL",
            str(Config.DEFAULT_CRD_COMPLETED_CHECK_INTERVAL),
        )
        try:
            interval = int(interval_str)
            if interval <= 0:
                logging.warning(
                    "CRD check interval must be positive.  Using default value: "
                    f"{Config.DEFAULT_CRD_COMPLETED_CHECK_INTERVAL}"
                )
                return Config.DEFAULT_CRD_COMPLETED_CHECK_INTERVAL
            return interval
        except ValueError:
            logging.error(
                "Invalid CRD check interval: {interval_str}. Defaulting to "
                "{Config.DEFAULT_CRD_COMPLETED_CHECK_INTERVAL} minutes."
            )
            return Config.DEFAULT_CRD_COMPLETED_CHECK_INTERVAL

    def _parse_time_value(self: Self, value: str | int, default_unit="m"):
        """Parse time value with optional suffix (h/m/s) and return in minutes."""
        if isinstance(value, int):
            return value

        value = str(value).strip().strip("\"'")

        if value.isdigit():
            return int(value)

        if value.endswith(("h", "m", "s")):
            num, unit = int(value[:-1]), value[-1]
            if unit == "h":
                return num * 60
            elif unit == "m":
                return num
            elif unit == "s":
                return max(1, num // 60)  # Convert to minutes, min 1

        raise ValueError(f"Invalid time format: {value}")

    @classmethod
    async def create(cls, **kwargs) -> "Config":
        """
        Asynchronous factory method to create a Config instance.
        This is useful for initializing resources that require async setup.
        """
        self: Config = cls()
        # determin if we need to set the _thin flag to True
        if "thin" in kwargs and kwargs["thin"]:
            self._thin = True
        await self.__ainit__()
        return self


# Initialize the config object
_config = None


async def load_config(thin: bool = False) -> Config:
    """Reload configuration from environment variables."""
    global _config
    _config = await Config.create(thin=thin)
    return _config


async def get_config(thin: bool = False) -> Config:
    """
    Returns the singleton instance of the Config class.
    """
    global _config
    if _config is None:
        _config = await Config.create(thin=thin)
    return _config


_cached_config = None


def get_config_sync(thin=False):
    """
    Synchronous version of get_config.
    Returns cached config if available, or creates a new one synchronously.
    """
    global _cached_config
    if _cached_config is not None:
        return _cached_config

    try:
        # Try to use existing event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Can't use run_until_complete in a running loop
            # Return default config
            config = Config()
            if thin:
                config._thin = True
            return config
        else:
            # Loop exists but isn't running, can use run_until_complete
            _cached_config = loop.run_until_complete(Config.create(thin=thin))
            return _cached_config
    except RuntimeError:
        # No event loop, create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _cached_config = loop.run_until_complete(Config.create(thin=thin))
        loop.close()
        return _cached_config
