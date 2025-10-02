# GCP GKE provider installation
Installing the IBM Symphony Host Factory GCP GKE provider generally follows the conventions established by the pre-installed Symphony Host Factory providers. Depends on the associated Kubernetes operator to be installed ( [Instructions](#../k8s-operator/README.md) )

* [Setup the provider plugin](#setup-the-provider-plugin)
* [Enable the provider plugin](#enable-the-provider-plugin)
* [Setup a provider instance](#setup-the-provider-instance)
* [Enable the provider instance](#enable-the-provider-instance)
* [Enable the requestor(s) to use the provider instance](#enable-the-requestors-to-use-the-provider-instance)

# Setup the provider plugin 
Suggested provider plugin directory name/location:
```
$HF_TOP/1.2/providerplugins/gcpgke/
```
Install the hf-provider executable and scripts via [RPMS](#rpm-packages) or [Building from source](#building-from-source)

## RPM packages
RPM packages to install the executable and scripts can be found [<FIXME> repo name](https://<FIXME>)
The RPM package's default `prefix` is `/opt/ibm/spectrumcomputing`. Use the rpm `--prefix` parameter to chose an alternative prefix if warranted.

## Building from source.
[README.md](./README.md) outlines building of the cli executable. The suggested providerplugin directory tree + scripts can be found under the [resources/gke_cli/1.2/providerplugins/gcpgke](./resources/gke_cli/1.2/providerplugins/gcpgke) directory. 

After building the cli executable, install it to the `bin` directory.

## Result
Using either method should result with a matching provider plugin directory:
```
├── bin
│   ├── hf-gke
│   └── README.md
└── scripts
    ├── getAvailableTemplates.sh
    ├── getRequestStatus.sh
    ├── getReturnRequests.sh
    ├── requestMachines.sh
    └── requestReturnMachines.sh
```

# Enable the provider plugin
Edit
```
$HF_TOP/conf/providerplugins/hostProviderPlugins.json
```
Add `gcpgke` provider plugin section:
```
        {
            "name": "gcpgke",
            "enabled": 1,
            "scriptPath": "${HF_TOP}/${HF_VERSION}/providerplugins/gcpgke/scripts/"
        }
```

# Setup a provider instance
Suggested provider instance directory name/location:
```
$HF_TOP/conf/providers/gcpgkeinst/
```

This directory tree and example files should be already present if using the [RPMS](#rpm-packages). If installing from source, the [resources/gke_cli/conf](./resources/gke_cli/conf/) directory contains recommended structure and example files that can be used to setup a new provider instance. In either case, the configuration files are described in greater detail in the following sections.

## Create gcpgkeinstprov_config.json
Copy `gcpgkeinstprov_config.json.dist` to `gcpgkeinstprov_config.json`

`GKE_KUBECONFIG` - defines the path to a/the kubectl config file. Default is `kubeconfig` in the provider instance directory, but can be pathed to an alternative kubectl config file.

### Example file:
```
{
  "GKE_KUBECONFIG": "KUBECONFIG"
}
```

The following configuration variables are supported in the gcpgkeinstprov_config.json file.

| Configuration Variable | Default Value | Description |
|------------------------|---------------|-------------|
| `GKE_KUBECONFIG`| | The filename with path of the configuration file used by the kubectl command.
| `GKE_CRD_NAMESPACE`*|`gcp-symphony`| Defines the kubernetes namespace in which all resources will be created
| `GKE_CRD_GROUP`*| `accenture.com` | The resource group used to identify the GKE HF Operator custom resources
| `GKE_CRD_VERSION`*| `v1` | The version used to identify GKE HF Operator custom resources
| `GKE_CRD_KIND`*| `GCPSympohonyResource` | The name given to the custom resource definition that defines a request for compute resources (pods)
| `GKE_CRD_SINGULAR`*| `gcp-symphony-resource` | Used in API calls when referring to a single GCPSymphonyResource custom resource instance.
| `GKE_CRD_RETURN_REQUEST_KIND`*| `MachineReturnRequest` | The name given to the custom resource definition that defines a request to return compute resources (pods)
| `GKE_CRD_RETURN_REQUEST_SINGULAR`*| `machine-return-request` | Used in API calls when referring to a single MachineReturnRequest custom resource instance
| `GKE_REQUEST_TIMEOUT`| `300` | In seconds, how long a request to the GKE control plane will wait for a response.
| `LOG_LEVEL`| `WARNING` | Controls the level of log detail that the GKE Provider writes to the log file. Options are `CRITICAL`, `WARNING`, `ERROR`, `INFO`, `DEBUG`.

***Note:** Changing any of the configurations items marked with an asterisk `*` will require syncing them with their counterparts in the kubernetes operator configuration. See [Operator CONFIG](../k8s-operator/docs/CONFIG.md) for details on related operator configuration.* **It is recommended to NOT change these values from the default.**


## Create gcpgkeinstprov_templates.json
Copy `gcpgkeinstprov_templates.json.dist` to `gcpgkeinstprov_templates.json`

Modify to suit, with the understanding that template attributes should be aligned with pod spec resources.  `pod-specs/pod-spec.yaml` documented in [pod-specs/pod-spec.yaml](#pod-specspod-specyaml) section

### Example file:
```
{
  "templates": [
    {
      "templateId": "template-gcp-01",
      "maxNumber": 5000,
      "attributes": {
        "type": [
          "String",
          "X86_64"
        ],
        "ncores": [
          "Numeric",
          "1"
        ],
        "ncpus": [
          "Numeric",
          "1"
        ],
        "nram": [
          "Numeric",
          "2048"
        ]
      },
      "podSpecYaml": "pod-specs/pod-spec.yaml"
    }
  ]
}
```
## kubeconfig
The default `gcpgkeinstprov_config.json` specifies a standard kubectl config file for the kubernetes cluster named `kubeconfig` within this provider instance directory. If following this default, ensure `kubeconfig` is a valid kubctl config file for your kubernetes cluster.

## pod-specs/pod-spec.yaml
Copy `pod-spec.yaml.dist` to `pod-spec.yaml`

By default, `gcpgkeinstprov_templates.json` specifies the use of a pod spec file named `pod-spec.yaml` in a `pod-specs` sub directory. The contents of this pod spec file should only contain the `spec:` section configuration of a standard kubernetes pod manifest. The contents of this file are passed to the operator, which builds the complete the pod manifest used to provision the Symphony machine pod(s). The contents of `pod-spec.yaml` should be adjusted to meet the requirements of the associated Symphony and Kubernetes clusters and aligned with the attributes of the `gcpgkeinstprov_templates.json` file.

### Example file:
```
# nodeSelector:  ## If using Custom Compute Class
#   cloud.google.com/compute-class: my-custom-compute-class
volumes:  ## If using a PV to access a shared symphony install
  - name: symphony
    persistentVolumeClaim:
      claimName: gcp-symphony-pvc
containers:
  - name: sym-compute
    image: rockylinux/rockylinux:8
    command: ["/bin/sh", "-c", "dnf install -y findutils libnsl procps java ; useradd egoadmin -u 1002; source /mnt/symphony-shared/spectrumcomputing/profile.platform; echo '10.0.0.6 symphony-management-0' >> /etc/hosts; egosh ego start; tail -f /dev/null "]
    securityContext:
      privileged: true
    stdin: true
    tty: true
    resources:
      requests:
        memory: "2048M"
    volumeMounts:  ## If using a PV to access a shared symphony install
      - mountPath: "/mnt/symphony-shared"
        name: symphony
```

## Resulting provider instance directory should match:
```
├── gcpgkeinstprov_config.json
├── gcpgkeinstprov_templates.json
├── kubeconfig
└── pod-specs
    └── pod-spec.yaml
```
# Enable the provider instance

Edit
```
$HF_TOP/conf/providers/hostProviders.json
```
Add `gcpgkeinst` provider instance section:
```
        {
            "name": "gcpgkeinst",
            "enabled": 1,
            "plugin": "gcpgke",
            "confPath": "${HF_CONFDIR}/providers/gcpgkeinst/",
            "workPath": "${HF_WORKDIR}/providers/gcpgkeinst/",
            "logPath": "${HF_LOGDIR}/"
        }
```

# Enable the requestor(s) instance to use the provider instance
Edit 
```
$HF_TOP/conf/requestors/hostRequestors.json
```

Add/replace the provider instance of the `providers` parameter of the appropriate requestor instance(s). E.g. `symAinst`, `admin`, or `cwsinst`

### Example providers parameter:
```
...
"providers": ["gcpgkeinst"],
...
```
