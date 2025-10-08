import os
from importlib.metadata import version as pkg_version, PackageNotFoundError


# this must match the project name described in pyproject.toml
_PROJECT_NAME = "google-symphony-hf"


def get_version() -> str:
    v = os.environ.get("HF_APP_VERSION")  # set by runtime hook in frozen app
    if v:
        return v
    try:
        return pkg_version(_PROJECT_NAME)  # when installed/editable
    except PackageNotFoundError:
        return "0.0.0-dev"
