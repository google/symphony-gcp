# About
This module provides the GCP HostFactory CLI (gcphf CLI). It should be called by the following scripts:
- getAvailableTemplates.sh
- requestMachines.sh
- requestReturnMachines.sh
- getRequestStatus.sh
- getReturnRequests.sh

In each case, the script should call the CLI, along with a command argument. For each case apart from `getAvailableTemplates.sh`, the script should also include  either a JSON string argument, or a `--json-file [filename]` argument.

Example:

requestMachines.sh

```
#!/usr/bin/env bash

gcphf requestMachines --json-file $2
```


# TODO: DOCUMENT
HF_PROVIDER_CONFDIR:
"GKE_KUBECONFIG": "kubeconfig",
HF_PROVIDER_LOGFILE:



# Installation

To install the CLI, use:

```bash
cd [PROJECT-ROOT/hf-provider]

# Install and activate venv via UV
# https://docs.astral.sh/uv/getting-started/installation/

# create the venv
uv venv

# activate the venv
source .venv/bin/activate

# install project dependencies
uv pip install -r pyproject.toml

# install pyinstaller
uv pip install pyinstaller

# create the hf-gce CLI for GCE clusters
PYTHONPATH=src pyinstaller --onefile src/gce_provider/__main__.py --name hf-gce --paths .venv/lib/python3.9/site-packages

# create the hf-gke CLI for GKE clusters
PYTHONPATH=src pyinstaller --onefile src/gke_provider/__main__.py --name hf-gke --paths .venv/lib/python3.9/site-packages

# example command
# Note: you will expect to see an error message if certain environment variables are not exported in your environment. 
# Please see section below for additional information
dist/hf-gce --help 
dist/hf-gke --help
```

The installed CLI executables can be moved to any location for execution, provided that the OS can support the version of Python used to build them. Both executables have been tested with Python 3.9.6.



# Running from Python

1. Ensure your environment variables are set properly. Importantly, you will want to ensure that `KUBECONFIG` and `HF_PROVIDER_CONFDIR` are set properly.
   - For the GKE Provider, you should specify:
     ```bash
     # This should already be exported if you have sourced the IBM Symphony environment variables.
     # You may need to modify the path depending on your environment.
     export HF_TOP=/opt/ibm/spectrumcomputing/hostfactory
     
     # This will be exported by HostFactory when executing the scripts, but you will need to export it manually to run the
     # script manually. You may need to modify the path depending on your environment.
     export HF_PROVIDER_CONFDIR=$HF_TOP/conf/providers/gcpgkeinst
     
     export KUBECONFIG=/path/to/kubeconfig
     ```
   - For the GCE Provider, you should specify:
     ```bash
     # This should already be exported if you have sourced the IBM Symphony environment variables.
     # You may need to modify the path depending on your environment.
     export HF_TOP=/opt/ibm/spectrumcomputing/hostfactory
     
     # This will be exported by HostFactory when executing the scripts, but you will need to export it manually to run the
     # script manually. You may need to modify the path depending on your environment.
     export HF_PROVIDER_CONFDIR=$HF_TOP/conf/providers/gcpgceinst
     
     export HF_DBDIR=$HF_TOP/db
     ```

        Notes:

        - This script has been tested with Python 3.9. Later versions of Python should be compatible.
        - You will need to have the provider configuration and host template configuration files configured in the `$HF_PROVIDER_CONFDIR` directory. Example files can be found in `hf-provider/tests/resources/`


2. Set the working directory to the root of this module.

3. Activate a virtual environment, e.g.: `uv venv; source .venv/bin/activate`

4. Install the project dependencies with `uv pip install -r pyproject.toml`

5. Execute the CLI using:
   ```bash
   # GCE provider
   PYTHONPATH=src python -m gce_provider --help
   
   # GKE provider
   PYTHONPATH=src python -m gke_provider --help
   ```
   This should give you a list of available commands.

6. For the following commands: `requestMachines`, `requestReturnMachines`, `getRequestStatus`, and `getReturnRequests`, you should include a JSON payload either as a string argument, or using `--json-file [payload file]`. Examples:
       
   ```bash
   PYTHONPATH=src python -m gke_provider getRequestStatus '{"machines": {"name": "foo"}}'
   ```

     or

     ```bash
     PYTHONPATH=src python -m gke_provider requestMachines --json-file ./test/resources/request-machines/request-machines-001.json
     ```

     The `--json-file` can be an absolute or relative path.



