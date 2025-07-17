# build_scripts/generate_version.py
import pathlib

import tomli

# Read version from pyproject.toml
pyproject_path = pathlib.Path(__file__).parent.parent / "pyproject.toml"
with open(pyproject_path, "rb") as f:
    pyproject_data = tomli.load(f)
    version = pyproject_data.get("project", {}).get("version", "whiskey.tango.hotel")

# Write version.py
version_path = (
    pathlib.Path(__file__).parent.parent
    / "src"
    / "gcp_symphony_operator"
    / "__init__.py"
)
with open(version_path, "w") as f:
    f.write(f'"""GCP Symphony Kubernetes Operator"""\n\n__version__ = "{version}"\n')
