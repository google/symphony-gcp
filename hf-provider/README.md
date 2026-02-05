# About
This module provides the GCP HostFactory CLI (hf-gce / hf-gke CLI). It should be called by the following scripts:
- getAvailableTemplates.sh
- requestMachines.sh
- requestReturnMachines.sh
- getRequestStatus.sh
- getReturnRequests.sh

In each case, the script should call the CLI, along with a command argument. For each case apart from `getAvailableTemplates.sh`, the script should also include either a JSON string argument or a `--json-file [filename]` argument.

Example:

```requestMachines.sh```

```
#!/usr/bin/env bash

hf-gce requestMachines --json-file $2
hf-gke requestMachines --json-file $2
```

# Environment Variables (HostFactory CLI / Provider)

|**Variable**| **Description**|
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `HF_PROVIDER_CONFDIR` | Directory where provider configuration is stored. Usually something like `$HF_TOP/conf/providers/<providerinst>` or directly referenced by provider instance scripts. |
| `HF_PROVIDER_LOGFILE` | Path to a log file for the HostFactory provider CLI or integration tools. Often used when logging outside the HostFactory default log directory. |
| `HF_TOP`              | Root directory for HostFactory installation. Defined in `hostfactory.xml` and used to locate provider and requestor plugins. ([IBM][1]) |
| `HF_CONFDIR`          | Directory for HostFactory configuration files. Defined in `hostfactory.xml`. ([IBM][1]) |
| `HF_WORKDIR`          | Work directory used by HostFactory and provider plugins. Defined in `hostfactory.xml`. ([IBM][1]) |
| `HF_LOGDIR`           | Log directory for HostFactory components. Defined in `hostfactory.xml`.([IBM][1]) |

[1]: https://www.ibm.com/docs/en/spectrum-symphony/7.3.2?topic=factory-hostfactoryxml "hostfactory.xml reference"


# Installation

This guide covers setting up the development environment, running tests, and building the CLI executables.

## Prerequisites

*   **Python 3.9+**
*   **uv**: A Python package installer and resolver. [Install uv](https://docs.astral.sh/uv/getting-started/installation/).

## Install Dependencies

1.  **Navigate to the project directory:**

    ```bash
    cd hf-provider
    ```

2.  **Create and activate a virtual environment:**

    ```bash
    uv venv
    source .venv/bin/activate
    ```

3.  **Install dependencies and PyInstaller:**

    ```bash
    uv pip install .
    uv pip install pyinstaller
    ```

## Unit Test

Run unit tests to ensure the setup is correct. These commands simulate the GitHub workflow.

```bash
# Run Common Tests
export HF_PROVIDER_CONFDIR=./tests/resources/provider-config/config-001/conf/providers/gcpgkeinst
python -m pytest tests/unit/common

# Run GCP GCE Provider Tests
export HF_PROVIDER_CONFDIR=./tests/resources/provider-config/config-001/conf/providers/gcpgceinst
python -m pytest tests/unit/gce_provider

# Run GCP GKE Provider Tests
export HF_PROVIDER_CONFDIR=./tests/resources/provider-config/config-001/conf/providers/gcpgkeinst
python -m pytest tests/unit/gke_provider
```

## Build CLIs

Build the standalone CLI executables for GCE and GKE providers.

```bash
# Build hf-gce CLI (GCE clusters)
uv run pyinstaller hf-gce.spec --clean

# Build hf-monitor CLI (GCE VM monitoring)
uv run pyinstaller hf-monitor.spec --clean

# Build hf-gke CLI (GKE clusters)
uv run pyinstaller hf-gke.spec --clean
```

**Verify the build:**

```bash
dist/hf-gce --help
dist/hf-gke --help
```

*Note: You may see errors about missing environment variables; this is expected at this stage.*

The executables are created in the `dist/` directory.

> **Important**: If using the GCE connector, `hf-gce` and `hf-monitor` must be in the same directory.

# Running from Python

1. Configure the environment for [GCE](./SYMPHONY_GCE_INSTALL.md) or [GKE](./SYMPHONY_GKE_INSTALL.md), depending on which provider you plan to use.
2. Ensure your environment variables are set properly. Importantly, you will want to ensure that `KUBECONFIG` and `HF_PROVIDER_CONFDIR` are set properly.
   - For the GKE Provider, you should specify:
     ```bash
     # This should already be exported if you have sourced the IBM Symphony environment variables.
     # You may need to modify the path depending on your environment.
     export HF_TOP=/opt/ibm/spectrumcomputing/hostfactory
     
     # This will be exported by HostFactory when executing the scripts, but you will need to export it manually to run the script.
     # You may need to modify the path depending on your environment.
     export HF_PROVIDER_CONFDIR=$HF_TOP/conf/providers/gcpgkeinst
     
     export KUBECONFIG=/path/to/kubeconfig
     ```
   - For the GCE Provider, you should specify:
     ```bash
     # This should already be exported if you have sourced the IBM Symphony environment variables.
     # You may need to modify the path depending on your environment.
     export HF_TOP=/opt/ibm/spectrumcomputing/hostfactory
     
     # This will be exported by HostFactory when executing the scripts, but you will need to export it manually to run the script.
     # You may need to modify the path depending on your environment.
     export HF_PROVIDER_CONFDIR=$HF_TOP/conf/providers/gcpgceinst
     ```

        Notes:

        - This script has been tested with Python 3.9.6 Later versions of Python should be compatible.
        - You will need to have the provider configuration and host template configuration files configured in the `$HF_PROVIDER_CONFDIR` directory. Example files can be found in `hf-provider/tests/resources/`

2. Set the working directory to the root of this module.

3. Activate a virtual environment, e.g.: `uv venv; source .venv/bin/activate`

4. Install the project dependencies with `uv pip install -r pyproject.toml`

5. Execute the CLI using:
   ```bash
   # GCE provider
   uv run hf-gce --help
   
   # GKE provider
   uv run hf-gke --help
   ```
   This should give you a list of available commands.

6. For the following commands: `requestMachines`, `requestReturnMachines`, `getRequestStatus`, and `getReturnRequests`, you should include a JSON payload either as a string argument, or using `--json-file [payload file]`. Examples:
       
   ```bash
   uv run hf-gke getRequestStatus '{"machines": {"name": "foo"}}'
   ```

     or

     ```bash
     uv run hf-gke requestMachines --json-file ./test/resources/request-machines/request-machines-001.json
     ```

     The `--json-file` can be an absolute or relative path.


