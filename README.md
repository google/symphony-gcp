# Google Symphony Host Factory

A comprehensive solution for integrating IBM Spectrum Symphony with Google Cloud Platform (GCP) compute resources, enabling dynamic provisioning and management of compute nodes on both Google Kubernetes Engine (GKE) and Google Compute Engine (GCE).

## Table of Contents

- [Overview](#overview)
- [Why This Project Exists](#why-this-project-exists)
- [Architecture](#architecture)
- [Components](#components)
  - [Host Factory Provider](#host-factory-provider)
  - [Kubernetes Operator](#kubernetes-operator)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Quick Start](#quick-start)
- [Use Cases](#use-cases)
  - [Cloud Bursting](#cloud-bursting)
  - [Hybrid Cloud Deployments](#hybrid-cloud-deployments)
  - [Development and Testing](#development-and-testing)
- [Project Status](#project-status)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)
- [Related Projects](#related-projects)

## <a id="overview"></a>Overview

This project provides two main components that work together to extend IBM Spectrum Symphony's Host Factory capabilities to Google Cloud Platform:

1. **Host Factory Provider** (`hf-provider/`) - CLI tools that interface with Symphony's Host Factory to provision and manage GCP resources
2. **Kubernetes Operator** (`k8s-operator/`) - A Kubernetes operator that manages Symphony compute pods in GKE clusters

## <a id="why-this-project-exists"></a>Why This Project Exists

IBM Spectrum Symphony's Host Factory provides dynamic resource provisioning capabilities, but lacks native support for Google Cloud Platform. This project bridges that gap by:

- **Enabling Cloud Bursting**: Allows Symphony clusters to dynamically scale into GCP when on-premises resources are insufficient
- **Cost Optimization**: Leverages GCP's spot instances and preemptible VMs for cost-effective compute scaling  
- **Unified Management**: Provides a consistent interface for managing both GKE pods and GCE instances through Symphony's existing Host Factory framework
- **Enterprise Integration**: Seamlessly integrates with existing Symphony deployments without requiring architectural changes

## <a id="architecture"></a>Architecture
This is an overview of the system architecture. Detailed documentation can be found [here](docs/architecture/README.md).

```
┌─────────────────────────────────────────────────────────────────┐
│                    IBM Spectrum Symphony                        │
│  ┌─────────────────┐    ┌─────────────────────────────────────┐ │
│  │   Host Factory  │────│        Provider Scripts             │ │
│  │                 │    │  • getAvailableTemplates.sh         │ │
│  │                 │    │  • requestMachines.sh               │ │
│  │                 │    │  • requestReturnMachines.sh         │ │
│  │                 │    │  • getRequestStatus.sh              │ │
│  │                 │    │  • getReturnRequest.sh              │ │
│  └─────────────────┘    └─────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────┐
│                  HF Provider CLI Tools                           │
│  ┌─────────────────┐              ┌─────────────────────────────┐│
│  │    hf-gce       │              │           hf-gke            ││
│  │  (GCE Provider) │              │       (GKE Provider)        ││
│  │                 │              │                             ││
│  │ • Instance      │              │ • Pod provisioning          ││
│  │   Groups        │              │ • Kubernetes API            ││
│  │ • Pub/Sub       │              │ • Custom Resources          ││
│  │ • Direct GCE    │              │                             ││
│  └─────────────────┘              └─────────────────────────────┘│
└──────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────┐
│                 Google Cloud Platform                            │
│  ┌─────────────────┐              ┌─────────────────────────────┐│
│  │  Compute Engine │              │   Kubernetes Engine (GKE)   ││
│  │                 │              │  ┌─────────────────────────┐││
│  │ • VM Instances  │              │  │    K8s Operator         │││
│  │ • Instance      │              │  │                         │││
│  │   Groups        │              │  │ • GCPSymphonyResource   │││
│  │ • Spot VMs      │              │  │ • MachineReturnRequest  │││
│  │                 │              │  │ • Pod Lifecycle Mgmt    │││
│  └─────────────────┘              │  └─────────────────────────┘││
└──────────────────────────────────────────────────────────────────┘
```

## <a id="components"></a>Components

### <a id="host-factory-provider"></a>Host Factory Provider (`hf-provider/`)

The Host Factory Provider contains CLI tools that implement Symphony's Host Factory plugin interface for GCP resources.

**Key Features:**
- **Dual Provider Support**: Separate providers for GCE and GKE workloads
- **Template-Based Provisioning**: Configurable resource templates aligned with Symphony requirements
- **Spot Instance Support**: Cost optimization through preemptible VM usage
- **Pub/Sub Integration**: Event-driven resource management for GCE instances

**Documentation:**
- [Provider README](hf-provider/README.md) - Installation and usage instructions
- [GCE Installation Guide](hf-provider/SYMPHONY_GCE_INSTALL.md) - Complete GCE provider setup
- [GKE Installation Guide](hf-provider/SYMPHONY_GKE_INSTALL.md) - Complete GKE provider setup

### <a id="kubernetes-operator"></a>Kubernetes Operator (`k8s-operator/`)

The Kubernetes Operator manages Symphony compute pods within GKE clusters, handling their complete lifecycle from provisioning to cleanup.

**Key Features:**
- **Custom Resource Definitions**: `GCPSymphonyResource` and `MachineReturnRequest` CRDs
- **Asynchronous Operations**: High-performance async processing for large-scale deployments
- **Preemption Handling**: Automatic detection and management of spot VM preemptions
- **Resource Cleanup**: Automated cleanup of completed resources with configurable retention
- **Health Monitoring**: Built-in health checks and status reporting

**Documentation:**
- [Operator README](k8s-operator/README.md) - Development setup and testing
- [Configuration Guide](k8s-operator/docs/CONFIG.md) - Environment variables and tuning
- [Quick Deploy Guide](k8s-operator/docs/QUICKDEPLOY.md) - Rapid deployment instructions
- [Troubleshooting Guide](k8s-operator/docs/operator-troubleshooting-guide.md) - Comprehensive troubleshooting

## <a id="getting-started"></a>Getting Started

### <a id="prerequisites"></a>Prerequisites

- IBM Spectrum Symphony cluster with Host Factory enabled
- Google Cloud Platform account with appropriate permissions
- For GKE: Kubernetes cluster (GKE recommended)
- For GCE: GCE project with Compute Engine API enabled

### <a id="quick-start"></a>Quick Start

1. **Choose Your Provider Type:**
   - **GKE Provider**: For containerized workloads in Kubernetes
   - **GCE Provider**: For traditional VM-based compute instances

2. **Install the Host Factory Provider:**
   ```bash
   cd hf-provider/
   # Follow installation instructions in README.md
   ```

3. **For GKE: Deploy the Kubernetes Operator:**
   ```bash
   cd k8s-operator/
   # Follow deployment instructions in SYMPHONY_GKE_INSTALL.md
   ```

4. **Configure Symphony Host Factory:**
   - Follow the appropriate installation guide (GCE or GKE)
   - Configure provider templates and instances
   - Enable the provider in Symphony's configuration

## <a id="use-cases"></a>Use Cases

### <a id="cloud-bursting"></a>Cloud Bursting
Scale Symphony workloads to GCP when on-premises capacity is exceeded:
- Automatic provisioning of additional compute resources
- Seamless integration with existing Symphony job scheduling
- Cost-effective scaling using spot instances

### <a id="hybrid-cloud-deployments"></a>Hybrid Cloud Deployments
Run Symphony workloads across on-premises and cloud infrastructure:
- Unified resource management through Symphony Host Factory
- Consistent job submission and monitoring experience
- Flexible resource allocation based on workload requirements

### <a id="development-and-testing"></a>Development and Testing
Provision temporary compute resources for development workflows:
- Rapid environment provisioning and teardown
- Cost optimization through automatic resource cleanup
- Isolated testing environments in the cloud

## <a id="project-status"></a>Project Status

- **Host Factory Provider**: Version 0.2.1 - Production ready
- **Kubernetes Operator**: Version 0.2.2 - Production ready

Both components are actively maintained and support production deployments.

## <a id="contributing"></a>Contributing

This project follows standard open-source contribution practices:

1. Fork the repository
2. Create a feature branch
3. Make your changes with appropriate tests
4. Submit a pull request

## <a id="license"></a>License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.

## <a id="support"></a>Support

For issues, questions, or contributions:
- Review the troubleshooting guides in each component's documentation
- Check existing issues in the project repository
- Submit new issues with detailed reproduction steps

## <a id="related-projects"></a>Related Projects

- <a href="https://www.ibm.com/products/spectrum-symphony" target="_blank">IBM Spectrum Symphony</a> - The core workload management platform
- <a href="https://cloud.google.com/kubernetes-engine" target="_blank">Google Kubernetes Engine</a> - Managed Kubernetes service
- <a href="https://cloud.google.com/compute" target="_blank">Google Compute Engine</a> - Virtual machine service
