Some important facts about this logging pipeline:

- Some logs might be duplicated. If they are, their timestamps will be equal or almost equal.
- The Symphony operator will respond the `getRequestStatus` query with a missing machine if it is preempted. This will make HostFactory trigger a `requestReturnMachines` that removes the corresponding machine.
- Once a machine is preempted, the associated MIG will try to recreate it with the same name. Depending on its capacity of recreating the machine, kubernetes will acknowledge the machine as being deleted or not. This will create a train of events of the form:
    - `node:not_ready`
    - `node:deleted` This can exist or not in function of the machine recreation speed / K8s acknowledgement of missing machine
    - `node:ready` 
    - `node:not_ready` The node will be re-deleted because the pod is deleted. 
    - `node:deleted`
- Due to the nature of the `pod:delete` LQL, one might see multiple entries for a single deletion. This is because the operator will delete the pod with a grace period of 30 seconds and then kubernetes will delete the pod without waiting. 