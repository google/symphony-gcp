# TODO

- [] Add startup indexing logic for multi-management local Symphony clusters.
- [] Check if multi compute node local Symphony clusters work.
- [] Add hability to disable need for the orchestrator project at the boostrap project.
    - [] Possibly modify architecture such that it uses cloud run / functions for log ingestion instead
- [] Add hability to programatically enable or disable usage of OS-login to the startup scripts / VMs metadata in order to enable usage of managed NFS.
- [] Improve orchestrator documentation.
- [] Search for and remove hardcoded variables such as registry URLs.
- [] Change BQIngestor from a pod to Cloud Run Function