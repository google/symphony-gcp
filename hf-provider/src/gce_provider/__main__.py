import argparse
import json
import os
import sys
from typing import Any, Callable, Optional

from pydantic import BaseModel

from common.model.models import (
    HFGetAvailableTemplatesResponse,
    HFRequestMachinesResponse,
    HFRequestReturnMachines,
    HFRequestStatus,
    HFReturnRequests,
    HFReturnRequestsResponse,
)
from common.utils.file_utils import load_json_file
from common.utils.path_utils import (
    normalize_path,
)
from gce_provider.commands.get_request_status import get_request_status
from gce_provider.commands.get_return_requests import get_return_requests
from gce_provider.commands.request_machines import request_machines
from gce_provider.commands.request_return_machines import request_return_machines
from gce_provider.config import Config, get_config
from gce_provider.db.initialize import main as initialize_db
from gce_provider.model.models import HFGceRequestMachines
from gce_provider.pubsub import launch_pubsub_daemon, main as monitor_events


#   1. Before running this module,
#      set up ADC as described in https://cloud.google.com/docs/authentication/external/set-up-adc
#   2. Replace the project variable.
#   3. Make sure that the user account or service account that you are using
#      has the required permissions.


class CommandNotFound(Exception):
    pass


class ValidCommands(dict[str, Callable[[Config, Optional[dict]], Optional[BaseModel]]]):
    def __missing__(self, key):
        raise CommandNotFound(f"Invalid command: {key}")


# specify the valid commands
valid_commands = ValidCommands(
    {
        "initializeDB": lambda config, payload: cmd_initialize_db(config, payload),
        "getAvailableTemplates": lambda config, payload: cmd_get_available_templates(
            config, payload
        ),
        "monitorEvents": lambda config, payload: cmd_monitor_events(config, payload),
        "requestMachines": lambda config, payload: cmd_request_machines(
            config, payload
        ),
        "requestReturnMachines": lambda config, payload: cmd_request_return_machines(
            config, payload
        ),
        "getRequestStatus": lambda config, payload: cmd_get_request_status(
            config, payload
        ),
        "getReturnRequests": lambda config, payload: cmd_get_return_requests(
            config, payload
        ),
    }
)


class NullOutput(BaseModel):
    """Indicates that output is intentionally empty"""

    pass


def cmd_initialize_db(config: Config, _: Optional[dict] = None) -> Optional[BaseModel]:
    """Initialize the event database"""
    initialize_db(config)
    return NullOutput()


def cmd_monitor_events(_: Config, __: Optional[dict]) -> Optional[BaseModel]:
    """Monitor GCE cloud events"""
    monitor_events()
    return NullOutput()


def cmd_get_available_templates(
    config: Config,
    payload: Optional[dict] = None,
) -> Optional[HFGetAvailableTemplatesResponse]:
    """
    Execute the getAvailableTemplates command
    :param config: the configuration
    :param payload: optional payload
    :return: the templates JSON
    """
    
    # Initialize the database to avoid the need to explicitly declare $HF_DBDIR,
    # thereby simplifying the installation process.
    initialize_db(config)

    config.logger.info(f"cmd_get_available_templates; payload={payload}")
    config.logger.info(f"hf_provider_conf_dir: {config.hf_provider_conf_dir}")
    if not config.hf_provider_conf_dir or not os.path.isdir(config.hf_provider_conf_dir):
        raise ValueError(f"Invalid directory path: {config.hf_provider_conf_dir}")
    templates_path = os.path.join(str(config.hf_provider_conf_dir), config.hf_templates_filename)
    config.logger.info(f"templates_path: {templates_path}")

    try:
        template_json = load_json_file(templates_path)
        response = HFGetAvailableTemplatesResponse.model_validate(template_json)
        return response
    except Exception as e:
        config.logger.error(f"Error while loading templates at {templates_path}: {e}")
        return None


def cmd_request_machines(
    config: Config, payload: Optional[dict] = None
) -> HFRequestMachinesResponse:
    """
    Execute the requestMachines command
    :param config: the configuration
    :param payload: the request payload
    :return: JSON response
    """
    if payload is None:
        raise ValueError("Must specify a JSON template")
    config.logger.info(f"cmd_request_machines {payload}")

    template_key = "templateId"
    template_value = payload.get("template")
    template_id = template_value.get(template_key) if template_value else None

    # get the template specified in the payload, so that we can determine the instance group and zone to include in
    # the request
    templates = cmd_get_available_templates(config)
    if templates is None:
        raise RuntimeError("Could not load available templates")

    templates_list = templates.templates
    if templates_list is None:
        raise ValueError("No templates found in the configuration")
    for template in templates_list:
        if template.get(template_key) == template_id:
            # we found the correct template, so now we formulate the request
            # and invoke the actual command script
            hf_request = HFGceRequestMachines(
                template=template_value,
                gcp_zone=template.get("gcp_zone"),
                gcp_instance_group=template.get("gcp_instance_group"),
            )
            config.logger.info(f"request: {hf_request}")
            return request_machines(hf_request)
    raise ValueError("Template is missing required attributes")


def cmd_request_return_machines(config: Config, payload: Optional[dict] = None):
    """
    Execute the requestMachines command
    :param config: the configuration
    :param payload: the request payload
    :return: JSON response
    """
    if payload is None:
        raise ValueError("Must specify a JSON template")
    config.logger.info(f"cmd_request_return_remachines {payload}")

    hf_request = HFRequestReturnMachines(machines=payload["machines"])
    config.logger.info(f"request: {hf_request}")
    return request_return_machines(hf_request)


def cmd_get_request_status(config: Config, payload: Optional[dict]):
    """
    Execute the getRequestStatus command
    :param config: the configuration
    :param payload: the request payload
    :return: JSON response
    """
    if payload is None:
        raise ValueError("Must specify the requests")
    config.logger.info(f"cmd_get_request_machine_status {payload}")

    hf_request = HFRequestStatus(requests=payload["requests"])
    config.logger.debug(f"request: {hf_request}")
    return get_request_status(hf_request)


def cmd_get_return_requests(
    config: Config, payload: Optional[dict]
) -> HFReturnRequestsResponse:
    """
    Execute the requestReturnRequests command
    :param config: the configuration
    :param payload: the request payload
    :return: JSON response
    """
    config.logger.info(f"cmd_get_return_requests {payload}")

    hf_request = HFReturnRequests(machines=payload["machines"])
    config.logger.info(f"request: {hf_request}")
    return get_return_requests(hf_request, config)


def dispatch_command(command: str, config: Config, payload: Optional[dict]):
    """
    Dispatch a command by executing the relevant service module
    :param command: The command argument
    :param config: the configuration
    :param payload: The JSON payload
    :return: The command's response
    """
    config.logger.info(f"DISPATCHING|command: {command}; payload: {json.dumps(payload)}")

    cmd = valid_commands.get(command)
    if cmd:
        result = cmd(config, payload)
        config.logger.info(f"DISPATCHED|command: {command}; result: {result}")
        if isinstance(result, NullOutput):
            return
        if result is not None:
            output = result.model_dump_json(
                indent=2,
                exclude_none=True,
            )
            config.logger.info(f"DISPATCHED|command: {command}; output: {output}")
            print(output)
            return
        else:
            ex = RuntimeError(f"DISPATCHING|command: {command}; ERROR: empty result")
            config.logger.error(ex)
            raise ex
    else:
        raise Exception(f"Invalid command: {cmd}")


def parse_args() -> tuple[str, Any]:
    """
    Parse the args from the script
    :return: the command and payload
    """
    parser = argparse.ArgumentParser(prog="hf-gce", description="GCP HostFactory Provider for GCE")

    parser.add_argument("command", choices=valid_commands)
    parser.add_argument("json", nargs="?")
    parser.add_argument("-f", "--json-file")

    args = parser.parse_args()

    payload = None
    if args.json is not None:
        try:
            payload = json.loads(args.json)
        except Exception as e:
            raise ValueError(f"Error while parsing JSON argument: {args.json}") from e
    elif args.json_file:
        json_path = normalize_path(os.getcwd(), args.json_file)
        try:
            payload = load_json_file(json_path)
        except Exception as e:
            raise ValueError(f"Error while loading json payload at {json_path}") from e

    return args.command, payload


def main():
    try:
        (command, payload) = parse_args()
        config = get_config()
        dispatch_command(command, config, payload)
        if config.pubsub_auto_launch:
            launch_pubsub_daemon()
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
