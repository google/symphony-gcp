from functools import lru_cache

from kubernetes import client, config

from gke_provider.config import get_config


@lru_cache(maxsize=1)
def load_kubernetes_config() -> None:
    """
    Load Kubernetes configuration from kubeconfig file or in-cluster config.
    """
    hf_config = get_config()
    logger = hf_config.logger

    try:
        logger.info(f"Loading kubeconfig from {hf_config.kube_config}")
        config.load_kube_config(hf_config.kube_config)
        logger.info("Loaded Kubernetes configuration from kubeconfig file.")
    except config.ConfigException:
        try:
            config.load_incluster_config()
            logger.info("Loaded Kubernetes in-cluster configuration.")
        except config.ConfigException as e:
            logger.error(f"Could not load Kubernetes configuration: {e}")
            raise


def get_kubernetes_client() -> client.ApiClient:
    """
    Get the Kubernetes API client.
    """
    load_kubernetes_config()
    return client.ApiClient()
