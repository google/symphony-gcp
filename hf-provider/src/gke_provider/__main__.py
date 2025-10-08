import argparse
import json
import os
import sys
from typing import Any, Dict, Optional

from typing_extensions import Self

from common.model.models import HFRequest
from common.utils.file_utils import load_json_file, load_yaml_file
from common.utils.path_utils import (
    normalize_path,
    resolve_caller_dir,
)
from common.utils.profiling import log_execution_time
from common.utils.version import get_version
from gke_provider.commands.get_request_machine_status import get_request_machine_status
from gke_provider.commands.get_return_requests import get_return_requests
from gke_provider.commands.request_machines import request_machines
from gke_provider.commands.request_return_machines import request_return_machines
from gke_provider.config import get_config

# Initialize configuration
config = get_config()


class CommandNotFound(Exception):
    pass


class ValidCommands(dict):
    def __missing__(self: Self, key: str) -> None:
        raise CommandNotFound(f"Invalid command: {key}")


# specify the valid commands
valid_commands = ValidCommands(
    {
        "getAvailableTemplates": lambda payload: cmd_get_available_templates(payload),
        "requestMachines": lambda payload: cmd_request_machines(payload),
        "requestReturnMachines": lambda payload: cmd_request_return_machines(payload),
        "getRequestStatus": lambda payload: cmd_get_request_machine_status(payload),
        "getReturnRequests": lambda payload: cmd_get_return_requests(payload),
    }
)

TEMPLATES_FILENAME = "gcpgkeinstprov_templates.json"


@log_execution_time(config.logger)
def cmd_get_available_templates(
    payload: Optional[dict] = None,
) -> Optional[Dict]:
    """
    Execute the getAvailableTemplates command
    :param payload: optional payload
    :return: the templates JSON
    """
    config.logger.info(f"cmd_get_available_templates; payload={payload}")
    config.logger.info(f"hf_provider_conf_dir: {config.hf_provider_conf_dir}")
    if not config.hf_provider_conf_dir or not os.path.isdir(
        config.hf_provider_conf_dir
    ):
        raise ValueError(f"Invalid directory path: {config.hf_provider_conf_dir}")
    templates_path = os.path.join(str(config.hf_provider_conf_dir), TEMPLATES_FILENAME)
    config.logger.info(f"templates_path: {templates_path}")

    try:
        return load_json_file(templates_path)
    except Exception as e:
        config.logger.error(f"Error while loading templates at {templates_path}: {e}")
        return None


@log_execution_time(config.logger)
def cmd_request_machines(payload: Optional[dict] = None) -> Optional[dict]:
    """
    Execute the requestMachines command
    :param payload: the request payload
    :return: JSON response
    """
    if payload is None:
        raise ValueError("Must specify a JSON template")
    config.logger.info(f"cmd_request_machines {payload}")

    template_key = "templateId"
    template_value = payload.get("template")
    template_id = template_value.get(template_key) if template_value else None

    # get the template specified in the payload
    templates = cmd_get_available_templates()
    if templates is None:
        msg = "Could not load available templates"
        config.logger.error(msg)
        raise RuntimeError(msg)

    templates_list = templates.get("templates")
    if templates_list is None:
        raise ValueError("No templates found in the configuration")
    for template in templates_list:
        if template.get(template_key) == template_id:
            # get the podspec
            podspec_yaml = template.get("podSpecYaml")
            config.logger.info(
                f"config.hf_provider_conf_dir: {config.hf_provider_conf_dir}"
            )
            config.logger.info(f"config.podspec_yaml: {podspec_yaml}")
            config.logger.info(
                f"normalized path: {normalize_path(config.hf_provider_conf_dir, podspec_yaml)}"
            )
            podspec_path = normalize_path(config.hf_provider_conf_dir, podspec_yaml)
            try:
                podspec = load_yaml_file(podspec_path)
            except Exception as e:
                config.logger.error(
                    f"Error while loading podspec at {podspec_path}: {e}"
                )
                podspec = None

            if podspec is None:
                error = ValueError(f"Could not find podspec at {podspec_path}")
                config.logger.error(error)
                raise error

            hf_request = HFRequest(
                requestMachines=payload,
                pod_spec=podspec,
            )  # type: ignore
            config.logger.info(f"request: {hf_request}")
            return request_machines(hf_request)
    return None


@log_execution_time(config.logger)
def cmd_request_return_machines(
    payload: Optional[dict] = None,
) -> Dict[str, Any]:
    """
    Execute the requestMachines command
    :param payload: the request payload
    :return: JSON response
    """
    if payload is None:
        raise ValueError("Must specify a JSON template")
    config.logger.info(f"cmd_request_return_remachines {payload}")

    hf_request = HFRequest(
        requestReturnMachines=payload,
    )  # type: ignore
    config.logger.info(f"request: {hf_request}")
    return request_return_machines(hf_request)


@log_execution_time(config.logger)
def cmd_get_request_status(
    payload: Optional[dict] = None,
) -> Optional[Dict[str, Any]]:
    """
    Execute the requestMachines command
    :param payload: the request payload
    :return: JSON response
    """
    if payload is None:
        raise ValueError("Must specify a JSON template")
    config.logger.info(f"cmd_get_request_status {payload}")

    hf_request = HFRequest(
        requestStatus=payload,
    )  # type: ignore
    config.logger.info(f"request: {hf_request}")
    return get_request_machine_status(hf_request)


@log_execution_time(config.logger)
def cmd_get_request_machine_status(
    payload: Optional[dict],
) -> Optional[dict[str, Any]]:
    """
    Execute the getRequestStatus command
    :param payload: the request payload
    :return: JSON response
    """
    if payload is None:
        raise ValueError("Must specify a JSON template")
    config.logger.info(f"cmd_get_request_machine_status {payload}")

    hf_request = HFRequest(
        requestStatus=payload,
    )  # type: ignore
    config.logger.info(f"request: {hf_request}")
    return get_request_machine_status(hf_request)


@log_execution_time(config.logger)
def cmd_get_return_requests(
    payload: Optional[dict],
) -> Optional[dict[str, Any]]:
    """
    Execute the requestReturnRequests command
    :param payload: the request payload
    :return: JSON response
    """
    if payload is None:
        raise ValueError("Must specify a JSON template")
    config.logger.info(f"cmd_get_return_requests {payload}")

    hf_request = HFRequest(returnRequests=payload)  # type: ignore
    config.logger.info(f"request: {hf_request}")
    return get_return_requests(hf_request)


@log_execution_time(config.logger)
def dispatch_command(command: str, payload: Optional[dict]):
    """
    Dispatch a command by executing the relevant service module
    :param command: The command argument
    :param payload: The JSON payload
    :return: The command's response
    """
    config.logger.info(
        f"DISPATCHING|command: {command}; payload: {json.dumps(payload)}"
    )

    cmd = valid_commands.get(command)
    if cmd:
        result = cmd(payload)
        config.logger.info(f"DISPATCHED|command: {command}; result: {result}")
        if result is not None:
            output = json.dumps(result, indent=2, sort_keys=True, default=str)
            config.logger.info(f"DISPATCHED|command: {command}; output: {output}")
            print(output)
            return
        else:
            config.logger.info(f"DISPATCHING|command: {command}; ERROR: empty result")
            print("ERROR: Command returned empty result")
            return
    else:
        raise Exception(f"Invalid command: {cmd}")


def parse_args() -> tuple[str, Any]:
    """
    Parse the args from the script
    :return: the command and payload
    """
    parser = argparse.ArgumentParser(
        prog="gcphf", description="GCP HostFactory Provider for GKE"
    )

    parser.add_argument("command", choices=valid_commands)
    parser.add_argument("json", nargs="?")
    parser.add_argument("-f", "--json-file")

    parser.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {get_version()}"
    )

    args = parser.parse_args()
    config.logger.debug(f"command is: {args.command}")
    config.logger.debug(f"json payload file is: {args.json_file}")

    payload = None
    if args.json is not None:
        payload = json.loads(args.json)
    elif args.json_file:
        config.logger.debug(f"args.json_file: '{args.json_file}'")
        config.logger.debug(f"Caller dir is {resolve_caller_dir()}")
        json_path = normalize_path(os.getcwd(), args.json_file)
        config.logger.debug(f"os.getcwd(): {os.getcwd()}")
        config.logger.debug(f"json_path: {json_path}")
        try:
            payload = load_json_file(json_path)
            config.logger.debug(f"Loaded JSON payload: {payload}")
        except Exception as e:
            config.logger.error(f"Error while loading json payload at {json_path}: {e}")

    return args.command, payload


def main() -> int:
    (command, payload) = parse_args()
    try:
        dispatch_command(command, payload)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    result = main()
    exit(result)
