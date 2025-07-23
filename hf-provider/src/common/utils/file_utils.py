import json
from typing import Optional

import yaml


def load_text_file(filepath: str) -> Optional[str]:
    try:
        with open(filepath, "r") as file:
            data = file.read()
            return data
    except FileNotFoundError as e:
        raise e
    except Exception as e:
        raise e


def load_json_file(filepath: str) -> Optional[dict]:
    try:
        with open(filepath, "r") as file:
            data = dict(json.load(file))
            return data
    except FileNotFoundError as e:
        raise e
    except json.JSONDecodeError as e:
        raise e
    except Exception as e:
        raise e


def load_yaml_file(filepath: str) -> Optional[dict]:
    try:
        with open(filepath, "r") as file:
            data = dict(yaml.safe_load(file))
            return data
    except FileNotFoundError as e:
        raise e
    except json.JSONDecodeError as e:
        raise e
    except Exception as e:
        raise e
