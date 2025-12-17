# GCP GCE Provider Installation
Installing the IBM Symphony Host Factory GCP GCE provider generally follows the conventions established by the pre-installed Symphony Host Factory providers. 

* [Set up the Google Cloud environment](#setup-the-google-cloud-environment)
* [Set up the provider plugin](#setup-the-provider-plugin)
* [Enable the provider plugin](#enable-the-provider-plugin)
* [Set up a provider instance](#setup-the-provider-instance)
* [Enable the provider instance](#enable-the-provider-instance)
* [Enable the requestor(s) to use the provider instance](#enable-the-requestors-to-use-the-provider-instance)



# Set up the Google Cloud environment 

## Prerequisites

- Create an Instance Group and Instance Template that meets the following requirements:
  - Autoscaling should be disabled, because scaling needs to be directly managed by the HostFactory provider.
  - New instances should be able to automatically launch the IBM Symphony services as a compute host.
  - The IBM Symphony Management Host has TCP connectivity to instances in the group.
- A service account that can manage the instance group, publish and subscribe to the required Pub/Sub topic, and access the associated logging resources. Make sure this account has the appropriate IAM roles for instance group operations, Pub/Sub interaction, and log writing or reading as required by your workflow.

## Set up Pub/Sub

1. Set up temporary shell variables.
   ```bash
   export GCP_PROJECT=<the name of the GCP project>
   export PUBSUB_TOPIC=hf-gce-vm-events
   ```
2. Create a Pub/Sub topic.
   ```bash
   gcloud pubsub topics create $PUBSUB_TOPIC
   ```
3. Create a logging sink to export audit logs to Pub/Sub
   ```bash
   gcloud logging sinks create ${PUBSUB_TOPIC}-sink \
     pubsub.googleapis.com/projects/${GCP_PROJECT}/topics/${PUBSUB_TOPIC} \
     --log-filter="
       logName=\"projects/${GCP_PROJECT}/logs/cloudaudit.googleapis.com%2Factivity\"
       resource.type=(\"gce_instance_group_manager\" OR \"gce_instance\")
       protoPayload.methodName=(
         \"v1.compute.instanceGroupManagers.createInstances\"
         OR
         \"v1.compute.instanceGroupManagers.deleteInstances\"
         OR
         \"v1.compute.instances.insert\"
         OR
         \"v1.compute.instances.delete\"
       )
     " \
     --description="Exports MIG VM create/delete audit logs to Pub/Sub"
   ```

   The command above is an example only. You should specify a more selective filter if you have other instance groups installed in this project.

   The command output will have a message similar to:

   ```bash
   Created [<https://logging.googleapis.com/v2/projects/symphony-dev-1/sinks/hf-gce-vm-events-sink>].
   Please remember to grant `serviceAccount:service-NNNNNNNNNN@gcp-sa-logging.iam.gserviceaccount.com` the Pub/Sub Publisher role on the topic.
   More information about sinks can be found at <https://cloud.google.com/logging/docs/export/configure_export>
   ```

   Note the service account named above, and use it the following step below:
4. Grant Pub/Sub publisher role.
   ```bash
   gcloud pubsub topics add-iam-policy-binding $PUBSUB_TOPIC \
     --member="serviceAccount:service-NNNNNNNNNN@gcp-sa-logging.iam.gserviceaccount.com" \
     --role="roles/pubsub.publisher"
   ```
5. Create a Pub/Sub subscription to receive the logs.
   ```bash
   gcloud pubsub subscriptions create ${PUBSUB_TOPIC}-sub \
     --topic=${PUBSUB_TOPIC}
   ```

   Take note of the name of the subscription that was created here, e.g. `my-pubsub-topic-sub`
6. Ensure that your service account has the correct permissions to subscribe to the subscription, e.g.:
   ```bash
   gcloud pubsub subscriptions add-iam-policy-binding <my-pubsub-topic-sub> \
    --member="serviceAccount:<my-service-account>@<my-project-id>.iam.gserviceaccount.com" \
    --role="roles/pubsub.subscriber"
   ```

**References:**

- [Publish and receive messages in Pub/Sub](https://cloud.google.com/pubsub/docs/publish-receive-messages-client-library)

 

# Set up the provider plugin 

Suggested provider plugin directory name/location:
```
$HF_TOP/$HF_VERSION/providerplugins/gcpgce/
```
Install the hf-provider executable and scripts via [RPMS](#rpm-packages) or [Building from source](#building-from-source)

## RPM packages
RPM packages to install the executable and scripts can be found [<FIXME> repo name](https://<FIXME>)
The RPM package's default `prefix` is `/opt/ibm/spectrumcomputing`. Use the rpm `--prefix` parameter to choose an alternative prefix if warranted.

## Building from source.
[README.md](./README.md) outlines building of the cli executable. The suggested providerplugin directory tree + scripts can be found under the [resources/gce_cli/1.2/providerplugins/gcpgce](./resources/gce_cli/1.2/providerplugins/gcpgce) directory. 

After building the cli executable, install it to the `bin` directory.

## Result
Using either method should result with a matching provider plugin directory:
```
├── bin
│   ├── hf-gce
│   ├── hf-monitor
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

# Set up a provider instance
Suggested provider instance directory name/location:
```
$HF_TOP/conf/providers/gcpgceinst/
```

This directory tree and example files should be already present if using the [RPMS](#rpm-packages). If installing from source, the [resources/gce_cli/conf](./resources/gce_cli/conf/) directory contains recommended structure and example files that can be used to set up a new provider instance. In either case, the configuration files are described in greater detail in the following sections.

## Create gcpgceinstprov_config.json
Copy `gcpgceinstprov_config.json.dist` to `gcpgceinstprov_config.json`

The following configuration variables are supported. Variables that have no default must be specified in the configuration.

| Variable Name           | Description                                                                                                                                                                                                                                                                                          | Default Value                                                                                                                |
| ----------------------- |------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------|
| `HF_DBDIR`              | The location where this provider should store its state database                                                                                                                                                                                                                                     | Defined in HostFactory environment as `$HF_DBDIR`                                                                            |
| `HF_TEMPLATES_FILENAME` | The name of the templates file                                                                                                                                                                                                                                                                       | `gcpgceinstprov_templates.json`                                                                                              |
| `GCP_CREDENTIALS_FILE`  | The location of the Google Cloud service account credentials file                                                                                                                                                                                                                                    | Will fallback to application default credentials if not specified                                                            |
| `GCP_PROJECT_ID`        | The ID of the Google Cloud project                                                                                                                                                                                                                                                                   | (None)                                                                                                                       |
| `GCP_INSTANCE_PREFIX`   | A string to prepend to all hosts created by this provider                                                                                                                                                                                                                                            | `sym-`                                                                                                                       |
| `LOGFILE`               | The location of the log file that the provider should log to                                                                                                                                                                                                                                         | A file with a generated name, located in the directory defined by the HostFactory environment variable `$HF_PROVIDER_LOGDIR` |
| `LOG_LEVEL`             | The Python log level                                                                                                                                                                                                                                                                                 | `WARNING`                                                                                                                    |
| `PUBSUB_TIMEOUT`        | If the most recent PubSub event was longer ago than this duration, in seconds, the PubSub listener will disconnect. This timeout only applies when the PubSub event listener is automatically launched. Otherwise, the listener will run indefinitely, and the admin should control the lifecycle.   | `600`                                                                                                                        |
| `PUBSUB_TOPIC`          | The name of the PubSub topic. This variable is for backwards compatibility only.                                                                                                                                                                                                                     | `hf-gce-vm-events`                                                                                                           |
| `PUBSUB_SUBSCRIPTION`   | The name of the PubSub subscription to monitor for VM events.                                                                                                                                                                                                                                        | `hf-gce-vm-events-sub`                                                                                                       |
| `PUBSUB_LOCKFILE`       | The name of the file to indicate that the PubSub event listener is active                                                                                                                                                                                                                            | `/tmp/sym_hf_gcp_pubsub.lock`                                                                                                |
| `PUBSUB_AUTOLAUNCH`     | If set to `true`, the provider will attempt to automatically launch the PubSub event listener. If `false`, you will need to launch the PubSub event listener manually, via the command `hf-monitor`. You can launch the daemon inline with a command, with the command `hf-gce <command> --monitor`. | `true`                                                                                                                       |
| `AUTO_RUN_TRIM_DB_CMD`     | Enables the provider to purge the provider database of inactive records. Setting this to `false` would allow for the creation of an batch process to run the trim command external from the provider execution. Make sure to point to the correct configuration file before running the command. | `true`                                                                                                                       |
| `RETURNED_VM_TTL`     | Determines how long a returned machine record remains in the database. Value is in days. Example: 30 means any machine older than 30 days will be permanently removed during cleanup. | `30`                                                                                                                       |

### Example file:
```
{
  "GCP_PROJECT_ID": "<CHANGEME-GCP_PROJECT_ID>",
  "LOG_LEVEL":"INFO",

  "PUBSUB_SUBSCRIPTION": "<CHANGEME-GCP_PUBSUB_SUBSCRIPTION>",
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