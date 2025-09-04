# GCP Symphony Kubernetes Operator

A Kubernetes operator for managing GCP Symphony Hostfactory related resources.

## Table of Contents

- [Change log](#change-log)
- [Development Setup](#development-setup)
  - [Installation](#installation)
  - [Running Tests](#running-tests)
  - [Code Quality](#code-quality)
- [Testing Configuration](#testing-config)
- [Exporting Manifests](#exporting-manifests)
- [Running the Operator](#running-operator)
- [Installing the operator to GKE](SYMPHONY_GKE_INSTALL.md)

[Return to the Google Symphony Hostfactory main readme](../README.md)

## <a id="change-log"></a>Change log

### Version 0.2.5
- Exposed option to enable/disable preemption handling logic. Defaulted to false.
- Exposed labels and taints variables to allow the user to specify a list of labels
  to identify VMs in the cluster that can be preempted by Google Compute Engine, and
  taints that would indicate a VM is being preempted.

### Version 0.2.4
- Updated GKE pod label for proper cluster attribution
- Refactored machine_return_request module to put pod deletion as its own function for use by
  the preemption handler.
- Updated preemption handler to delete pods directly rather than generate a new mrr (rrm) CRD.
- Added proper tagging/labels to GKE pods for appropriate attribution tracking.

### Version 0.2.3
- Dockerfile updates to allow for passing a VERSION for a more detailed tagging label, if desired.
- No functional changes with operator code

### Version 0.2.2
- Cleanup of project dependencies
- No functional changes with operator code

### Version 0.2.1
- Corrected element names for GCPSymphonyResources in code to fix missing returnTime on
GCPSR status for returnedMachines
- Corrected logic that determines GCPSR phase value.

### Version 0.2.0
- Moved all relevant functions to asynchronous operation.
- Added status_update worker for managing the resource event queue
- Updated the default `CRD_COMPLETED_RETAIN_TIME` to 1440 minutes (24 hours).
- Refactored modules for easier understanding and improved code maintainability.
- Added logic to ensure `Completed` conditions were always added to the GCPSymphonyResource

### Version 0.1.9
- No one talks about verison 0.1.9

### Version 0.1.8
- Added a MachineReturnRequest custom resource to allow the operator to handle removal of pods
that HostFactory returns, improving performance of the CLI.

### Version 0.1.3
- Added a resource cleanup handler to operate on a timer. This will check for GCPSymphonyResource type resources that has no more active pods. If the time since the last pod was deleted is longer than the `CRD_COMPLETED_RETAIN_TIME` environment variable (default 120 minutes), the resource will be deleted.
- Added new cluster role permission for the service account. Please redeploy the operator_clusterrole.yaml from the `python -m gcp_symphony_operator export-manifests --separate-files` output prior to running this version if you're upgrading from a previouse version.  



## <a id="development-setup"></a>Development Setup

### Prerequisites

- Python 3.12+
- pip
- Kubernetes cluster for testing (minikube, kind, etc.)

These instructions will descring the use of `uv`, "an extremely fast Python package manager."  It is recommended to use `uv` as the document describes, but it is not a hard requirement.

### <a id="installation"></a>Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd k8s-operator
```

2. Install the package in development mode:

```bash
uv pip install -e ".[dev]"

```

*The following items assume the user is logged into the k8s-operator directory of the repository.*

### <a id="running-tests"></a>Running Tests

Run all tests:

```bash
pytest test
```


### <a id="code-quality"></a>Code Quality

Format code:

```bash
black src
```

Run linters:

```bash
flake8 src
```

## <a id="testing-config"></a>Testing Configuration

The project uses pytest for testing with the following configuration:

- `pytest.ini`: Defines test paths, naming conventions, and coverage settings
- `setup.cfg`: Contains configuration for code quality tools (flake8, isort, mypy)
- `requirements-dev.txt`: Lists development dependencies

### Test Structure

- `tests/`: Root directory for all tests
  - `conftest.py`: Common fixtures for tests
  - `test_unit/` : directory containing all unit tests
    - `test_*.py`: Test modules
    - `*/test_*.py`: Test modules in subdirectories mirroring the source structure

### Test Markers

- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.slow`: Slow running tests


## <a id="exporting-manifests"></a>Exporting Manifests
In order to run the operator locally, the custom resource definitions, will need to be deployed into the target kubernetes cluster. To get all of the manifest for deploying, run the following commands:

```bash
cd src
python -m gcp_symphony_operator export-manifests > /path/to/store/gcp-operator-manifests.yaml
```
Review the manifests file. If the operator will be run locally for debugging, be sure to remove the Deployment section of the manifest found at the end of the file.
Apply the rest of the manifest with the following command:
```bash
kubectl apply -f /path/to/store/gccp-operator-manifests.yaml
```

## <a id="running-operator"></a>Running the Operator

It is possible to run the operator locally, connect to a remote (or local) kubernetes cluster and debug. If not using a debugger and it's desired to simply run the operator without deploying it use the following commands:

```bash
export GCP_HF_KUBECONFIG_PATH=</path/to/valid/kubernetes/config>
cd src
python -m gcp_symphony_operator
```
