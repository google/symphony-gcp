# TODO

- [] Add startup indexing logic for multi-management local Symphony clusters.
- [] Check if multi compute node local Symphony clusters work.
- [] Add hability to disable need for the orchestrator project at the boostrap project.
    - [] Possibly modify architecture such that it uses cloud run / functions for log ingestion instead
- [] Add hability to programatically enable or disable usage of OS-login to the startup scripts / VMs metadata in order to enable usage of managed NFS.
- [] Improve orchestrator documentation.
- [] Search for and remove hardcoded variables such as registry URLs.
- [] Change BQIngestor from a pod to Cloud Run Function
- [] Upgrade architecture for master IP/hostname propagation accross new compute nodes after failover event. Possible solutions:
    - internal cloud DNS -> Requires triggering update on fail-over / keeps same hostname/IP -> might cause Symphony problems
    - internal load balancer -> Might not require triggering update on fail-over / keeps same hostname/IP -> might cause Symphony problems
    - store primary name in GCS, pull from GCS -> Requires triggering update on fail-over / changes hostname/IP
    - MIG metadata / service registry (GCP Service Directory) -> Requires triggering update on fail-over / changes hostname 
- [] For final release rename the orchestrator BQ table to logs and change corresponding code. Delete legacy table code.
- [] Modify startup scripts to add idempotency to installation