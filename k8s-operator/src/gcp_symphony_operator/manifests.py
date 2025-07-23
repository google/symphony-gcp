import asyncio
import importlib.resources
import os
import sys
from typing import Any, Dict, Optional, Union

import yaml
from jinja2 import Environment, FileSystemLoader
from typing_extensions import Self

from .config import Config, get_config


class Manifests:
    """Class to represent the Kubernetes manifests for the GCPSymphonyResources."""

    """Class to represent the Kubernetes manifests for the GCPSymphonyResources."""

    _instance = None
    __initialized = False
    __initialized = False

    def __new__(cls, config: Optional[Config] = None) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.__initialized = False
        return cls._instance

    def __init__(self, config: Optional[Config] = None):
        if self.__initialized:
            return

        #######################################################################
        # Load manifests into the config object These are used for generating
        #  manifests for deployment into a kubernetes cluster. The rendered
        #  manifests will be specific to the environment and the values set
        #  in the environment variables above.
        #######################################################################

        if config is None:
            config = asyncio.run(get_config(thin=True))

        # Initialize Jinja2 environment for CRD path
        self.template_env = Environment(
            loader=FileSystemLoader(
                self._get_resource_path(config.crd_manifest_path), followlinks=True
            ),
            autoescape=True,
        )

        # Load CRD manifest
        crd_manifest = self._load_and_render_manifest(
            config.crd_manifest_file,
            {
                "crd_group": config.crd_group,
                "crd_api_version": config.crd_api_version,
                "crd_kind": config.crd_kind,
                "crd_plural": config.crd_plural,
                "crd_singular": config.crd_singular,
                "crd_short_name": config.crd_short_name,
                "crd_finalizer": config.crd_finalizer,
            },
        )

        # Load the delete request CRD manifest
        return_request_manifest = self._load_and_render_manifest(
            config.crd_return_request_manifest_file,
            {
                "crd_group": config.crd_group,
                "crd_api_version": config.crd_api_version,
                "pdr_kind": config.crd_return_request_kind,
                "pdr_plural": config.crd_return_request_plural,
                "pdr_singular": config.crd_return_request_singular,
                "pdr_short_name": config.crd_return_request_short_name,
            },
        )

        # Set Jinja2 environment for namespace path
        self.template_env = Environment(
            loader=FileSystemLoader(
                self._get_resource_path(config.namespace_manifest_path),
                followlinks=True,
            ),
            autoescape=True,
        )

        # load namespace manifest
        namespace_manifest = self._load_and_render_manifest(
            config.namespace_manifest_file, {"namespace": config.default_namespaces[0]}
        )

        # Set Jinja2 environment for RBAC path
        self.template_env = Environment(
            loader=FileSystemLoader(
                self._get_resource_path(config.rbac_manifest_path), followlinks=True
            ),
            autoescape=True,
        )

        # load RBAC manifests - Service Account
        service_account = self._load_and_render_manifest(
            config.service_account_file,
            {
                "service_account_name": config.service_account_name,
                "namespace": config.default_namespaces[0],
            },
        )

        # load RBAC manifests - role
        default_namespace_role = self._load_and_render_manifest(
            config.namespace_role_file,
            {
                "namespace_role_name": config.namespace_role_name,
                "namespace": config.default_namespaces[0],
                "crd_group": config.crd_group,
                "crd_plural": config.crd_plural,
                "crd_return_request_plural": config.crd_return_request_plural,
            },
        )

        # load RBAC manifest - cluster role
        default_cluster_role = self._load_and_render_manifest(
            config.cluster_role_file,
            {
                "cluster_role_name": config.cluster_role_name,
                "crd_group": config.crd_group,
                "crd_plural": config.crd_plural,
                "crd_return_request_plural": config.crd_return_request_plural,
            },
        )

        # load RBAC manifests - role binding
        default_namespace_role_binding = self._load_and_render_manifest(
            config.namespace_role_binding_file,
            {
                "namespace_role_binding_name": config.namespace_role_binding_name,
                "namespace_role_name": config.namespace_role_name,
                "service_account_name": config.service_account_name,
                "namespace": config.default_namespaces[0],
            },
        )

        # load RBAC manifests - cluster role binding
        default_cluster_role_binding = self._load_and_render_manifest(
            config.cluster_role_binding_file,
            {
                "cluster_role_binding_name": config.cluster_role_binding_name,
                "cluster_role_name": config.cluster_role_name,
                "service_account_name": config.service_account_name,
                "namespace": config.default_namespaces[0],
            },
        )

        # load an operator deployment manifest
        self.template_env = Environment(
            loader=FileSystemLoader(
                self._get_resource_path(config.manifest_base_path), followlinks=True
            ),
            autoescape=True,
        )
        self.operator_manifest = self._load_and_render_manifest(
            config.operator_manifest_file,
            {
                "operator_name": config.operator_name,
                "operator_image_tag": config.operator_image_tag,
                "container_image": config.default_container_image,
                "container_image_pull_policy": config.default_container_image_pull_policy,
                "service_account_name": config.service_account_name,
                "log_level": config.log_level,
                "namespace": config.default_namespaces[0],
                "default_namespaces": config.default_namespaces,
                "operator_version": config.operator_version,
            },
        )

        # put all of the manifests into a dictionary for easy access
        self.manifests = {
            "namespace": namespace_manifest,
            "crd": crd_manifest,
            "return_request_crd": return_request_manifest,
            "service_account": service_account,
            "role": default_namespace_role,
            "cluster_role": default_cluster_role,
            "role_binding": default_namespace_role_binding,
            "cluster_role_binding": default_cluster_role_binding,
            "operator": self.operator_manifest,
        }

        self.__initialized = True

    def _load_and_render_manifest(
        self: Self, template_file: str, template_vars: Dict[str, Any]
    ) -> Union[Any, Dict[Any, Any]]:
        """Loads a Jinja2 template, renders it with the given variables, and parses the YAML."""
        try:
            template = self.template_env.get_template(template_file)
            rendered_manifest = template.render(template_vars)
            return yaml.safe_load(rendered_manifest)
        except Exception as e:
            print(f"\nError loading and rendering manifest {template_file}: {e}")
            return (
                {}
            )  # Or raise the exception, depending on your error handling strategy

    def export_manifest(
        self, target_path: str, separate_files: Optional[bool] = False
    ) -> None:
        """
        Export the rendered manifests to YAML files.
        If separate_files is True, each manifest will be saved in its own file.
        If False, all manifests will be saved in a single file.
        """
        if not self.__initialized:
            print("Manifests have not been loaded. Please run load_manifests() first.")
            return

        # send output to standart out
        if separate_files:
            if target_path == "-":
                target_path = "."
            for name, manifest in self.manifests.items():
                filepath = os.path.join(target_path, f"{name}.yaml")
                with open(filepath, "w") as output:
                    output.write("---\n")
                    yaml.dump(manifest, output, indent=2)
                print(f"Manifest '{name}' exported to {filepath}")
        else:
            out = sys.stdout
            for name, manifest in self.manifests.items():
                yaml.dump(manifest, out, indent=2)
                out.write("---\n")

    def crd_manifest(self) -> dict:
        """Return the CRD manifest."""
        return dict(self.manifests["crd"])

    def return_request_manifest(self) -> dict:
        """Return the CRD manifest."""
        return dict(self.manifests["return_request_crd"])

    def _get_resource_path(self, resource_path: str) -> str:
        """Get the absolute path to a resource within the package."""
        try:
            # Use importlib.resources to get the path to the resource
            resource_package = __name__.split(".")[
                0
            ]  # Assuming the package name is the first part of __name__
            resource_location = (
                importlib.resources.files(resource_package) / resource_path
            )
            return str(resource_location)
        except Exception as e:
            print(f"Error getting resource path: {e}")
            # Fallback to a path relative to the current file (for development)
            return os.path.abspath(
                os.path.join(os.path.dirname(__file__), resource_path)
            )

    def get_manifest(self, manifest_name: Union[str, None] = None) -> dict:
        if manifest_name in self.manifests:
            return dict(self.manifests[manifest_name])
        else:
            return self.manifests
