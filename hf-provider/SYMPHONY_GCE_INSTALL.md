# GCP GCE provider installation
Installing the IBM Symphony Host Factory GCP GCE provider generally follows the conventions established by the pre-installed Symphony Host Factory providers. 

* [Setup the provider plugin](#setup-the-provider-plugin)
* [Enable the provider plugin](#enable-the-provider-plugin)
* [Setup a provider instance](#setup-the-provider-instance)
* [Enable the provider instance](#enable-the-provider-instance)
* [Enable the requestor(s) to use the provider instance](#enable-the-requestors-to-use-the-provider-instance)

# Setup the provider plugin 
Suggested provider plugin directory name/location:
```
$HF_TOP/1.2/providerplugins/gcpgce/
```
Install the hf-provider executable and scripts via [RPMS](#rpm-packages) or [Building from source](#building-from-source)

## RPM packages
RPM packages to install the executable and scripts can be found [<FIXME> repo name](https://<FIXME>)
The RPM package's default `prefix` is `/opt/ibm/spectrumcomputing`. Use the rpm `--prefix` parameter to chose an alternative prefix if warranted.

## Building from source.
[README.md](./README.md) outlines building of the cli executable. The suggested providerplugin directory tree + scripts can be found under the [resources/gce_cli/1.2/providerplugins/gcpgce](./resources/gce_cli/1.2/providerplugins/gcpgce) directory. 

After building the cli executable, install it to the `bin` directory.

## Result
Using either method should result with a matching provider plugin directory:
```
├── bin
│   ├── hf-gce
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
Add `gcpgce` provider plugin section:
```
        {
            "name": "gcpgce",
            "enabled": 1,
            "scriptPath": "${HF_TOP}/${HF_VERSION}/providerplugins/gcpgce/scripts/"
        }
```

# Setup a provider instance
Suggested provider instance directory name/location:
```
$HF_TOP/conf/providers/gcpgceinst/
```

This directory tree and example files should be already present if using the [RPMS](#rpm-packages). If installing from source, the [resources/gce_cli/conf](./resources/gce_cli/conf/) directory contains recommended structure and example files that can be used to setup a new provider instance. In either case, the configuration files are described in greater detail in the following sections.

## Create gcpgceinstprov_config.json
Copy `gcpgceinstprov_config.json.dist` to `gcpgceinstprov_config.json`

Only one value typically needs to be modified:
* `GCP_PROJECT_ID`  - defines the Id of the GCP project

### Example file:
```
{
  "GCP_PROJECT_ID": "<CHANGEME-GCP_PROJECT_ID>",
  "LOG_LEVEL":"INFO",
  "LOG_MAX_FILE_SIZE": 10,
  "LOG_MAX_ROTATE": 5,
  "ACCEPT_PROPAGATED_LOG_SETTING": true,

  "PUBSUB_TIMEOUT": 100
}
```

## Create gcpgceinstprov_templates.json
Copy `gcpgceinstprov_templates.json.dist` to `gcpgceinstprov_templates.json`

Two values typically needs to be modified:
* gcp_zone - <FIXME>
* gcp_instance_group - <FIXME>

Modify to suit, with the understanding that the attributes should be aligned with the configuration of the supporting instance group.

### Example file:
```
{
  "templates": [
    {
      "templateId": "template-gcp-01",
      "maxNumber": 10,
      "attributes": {
        "type": [
          "String",
          "X86_64"
        ],
        "ncpus": [
          "Numeric",
          "1"
        ],
        "nram": [
          "Numeric",
          "1024"
        ]
      },
      "gcp_zone": "<CHANGEME-gcp_zone>",
      "gcp_instance_group": "<CHANGEME-gcp_instance_group>"
    }
  ]
}
```

## Resulting provider instance directory should match:
```
├── gcpgceinstprov_config.json
└── gcpgceinstprov_templates.json
```

# Enable the provider instance

Edit
```
$HF_TOP/conf/providers/hostProviders.json
```
Add `gcpgceinst` provider instance section:
```
        {
            "name": "gcpgceinst",
            "enabled": 1,
            "plugin": "gcpgce",
            "confPath": "${HF_CONFDIR}/providers/gcpgceinst/",
            "workPath": "${HF_WORKDIR}/providers/gcpgceinst/",
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
"providers": ["gcpgceinst"],
...
```
