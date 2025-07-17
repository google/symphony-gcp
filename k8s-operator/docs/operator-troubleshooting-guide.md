# GCP Symphony Operator Troubleshooting Guide

This guide helps system administrators and support teams understand and troubleshoot GCPSymphonyResource (GCPSR) and MachineReturnRequest (MRR) states in the GCP Symphony Operator.

## Table of Contents

- [Resource Types Overview](#resource-type-overview)
- [Best Practices](#best-practices)
- [Alert Conditions](#alert-conditions)
- [Key Fields to Monitor](#key-fields)
- [Scenario Analysis](#scenario-analysis)
  - [1. Normal Pod Provisioning (During Startup)](#normal-gcpsr)
  - [2. Healthy Running State](#healthy-gcpsr)
  - [3. Mixed Return Scenario](#mixed-return)
  - [4. Node Death/Preemption Scenario](#node-death)
  - [5. Normal Return Process](#normal-return)
- [Troubleshooting Commands](#troubleshooting-commands)
  - [Check Resource Status](#check-resource-status)
  - [Monitor Resource Lifecycle](#monitor-resource-lifecycle)
- [Common Issues and Solutions](#common-issues)
  - [Stuck in Pending Phase](#stuck-in-pending-phase)
  - [Pods Not Returning](#pods-not-returning)
  - [High Failed Machine Count](#high-failed-machine-count)
  - [Pods Not deleting](#pods-not-deleting)
  - [GCPSymphonyResource in WaitingCleanup state](#gcpsr-waiting-cleanup)

## <a id="resource-type-overview"></a>Resource Types Overview

- **GCPSymphonyResource (GCPSR)**: Manages the lifecycle of compute pods for Symphony workloads
- **MachineReturnRequest (MRR)**: Handles the return/cleanup of compute resources


## <a id="best-practices"></a>Best Practices

1. **Regular Monitoring**: Check resource status during peak usage periods
2. **Log Retention**: Maintain operator logs for troubleshooting historical issues
3. **Resource Cleanup**: Monitor for resources stuck in `WaitingCleanup` phase
4. **Capacity Planning**: Track `availableMachines` vs requested to identify capacity constraints. ***Note:*** As spot or preemptable VMs are reclaimed by the cloud provider, the number of `availableMachines` may decrease and will not return to match `machineCount`. This is normal.
5. **Spot Instance Awareness**: Expect frequent node death scenarios when using spot instances. The GCP Symphony Operator will ***not*** try to bring any failed pods up on new nodes. Pods that are lost due to node (VM) preemption are gone for good.


## <a id="alert-conditions"></a>Alert Conditions

Here are a few suggestions for monitoring alerts:
- GCPSR stuck in `Pending` phase > 10 minutes
- MRR with `failedMachines` > 0
- GCPSR with `availableMachines` significantly less than `machineCount` for extended periods
- Resources with `symphony.waitingCleanup` label that don't progress to completion


## <a id="key-fields"></a>Key Fields to Monitor

### GCPSymphonyResource Status Fields
- `phase`: Current lifecycle phase (Pending, Running, WaitingCleanup, Completed)
- `availableMachines`: Number of ready compute pods
- `conditions`: Detailed status conditions with timestamps
- `returnedMachines`: List of pods that have been returned

### MachineReturnRequest Status Fields
- `phase`: Current phase (Pending, InProgress, Completed, Failed, PartiallyCompleted)
- `totalMachines`: Total number of machines to return
- `returnedMachines`: Number successfully returned
- `failedMachines`: Number that failed to return
- `machineEvents`: Per-machine status details


## <a id="scenario-analysis"></a>Scenario Analysis

### <a id="normal-gcpsr"></a>1. Normal Pod Provisioning (During Startup)

**Indicators on a GCPSymphonyResource (gcpsr):**
- Phase: `Pending`
- `availableMachines` < `spec.machineCount`
- Conditions show `ContainersReady` for some pods

**Example:**
```yaml
spec:
  machineCount: 15
  ...
status:
  availableMachines: 3
  conditions:
  - lastTransitionTime: "2025-07-10T21:32:16.603502+00:00"
    message: All containers in pod g1c733ee2-1b4b-41ca-bab4-d8a23b52ade8-8s2rw-pod-2
      are ready
    reason: ContainersReady
    status: "True"
    type: ContainerHealth
  phase: Pending
```

**What's happening:** Pods are being created and containers are starting up. This is normal during resource provisioning. Note that the ContainerHealth condition will only show the condition of the last pod that transitioned into ready status.

**Action:** Monitor progress. If stuck for >10 minutes, check node capacity and image pull status.

### <a id="healthy-gcpsr"></a>2. Healthy Running State

**Indicators:**
- Phase: `Running`
- `availableMachines` = `spec.machineCount`

**Example:**
```yaml
spec:
  machineCount: 10
  ...
status:
  availableMachines: 10
  ...
  phase: Running
```

**What's happening:** All requested pods are running and healthy.

**Action:** No action needed. System is operating normally.

### <a id="mixed-return"></a>3. Mixed Return Scenario

**Indicators on a GCPSymphonyResource (gcpsr):**
- Phase: `WaitingCleanup`
- Label: `symphony.waitingCleanup: "True"`
- Mix of `system-initiated-return` and user-initiated returns in `returnedMachines`
- Conditions show both `PodReturned` and `Completed`

**Example:**
```yaml
status:
  phase: WaitingCleanup
  returnedMachines:
  - name: pod-5
    returnRequestId: system-initiated-return    # A cloud-provider or manual delete
    returnTime: "2025-03-10T21:18:58.202667+00:00"
  - name: pod-0
    returnRequestId: c547ff1a-38a7-44df-9f6e-50073e399a4d  # Symphony HostFactory request
    returnTime: "2025-03-10T21:24:08.266732+00:00"
```

**What's happening:** Some pods were returned by the system (likely due to node issues) and others by Symphony HostFactory.

**Action:** Verify if cleanup completed successfully. Check for any stuck pods. If any stuck pods do not have a corresponding GCPSR, but they still have the `symphony-operator/finalizer` finalizer attached, patch the pod to remove the finalizer so that the control plane can continue to delete it. A sample command would be

```bash
kubectl patch pod <pod-name> --type=json -p='[{"op": "remove", "path": "/metadata/finalizers", "value": "symphony-operator/finalizer"}]'-n <namespace>
```

### <a id="node-death"></a>4. Node Death/Preemption Scenario

**Indicators in MachineReturnRequest (mrr):**
- All machine events show: `"Pod does not exist, marked as completed"`
- `returnTime` timestamps are identical
- Phase: `Completed`
- `failedMachines: 0`

**Example:**
```yaml
machineEvents:
  pod-3:
    message: Pod does not exist, marked as completed
    returnRequestTime: "2025-04-10T21:19:15.375746+00:00"
    status: Completed
  pod-4:
    message: Pod does not exist, marked as completed
    returnRequestTime: "2025-04-10T21:19:15.375746+00:00"
    status: Completed
```

**What's happening:** Kubernetes nodes were terminated (likely spot instance preemption), causing pods to disappear.

**Action:** Normal behavior for spot instances. Monitor for new resource requests if workload continues.

### <a id="normal-return"></a>5. Normal Return Process

**Indicators in MachineReturnRequest (mrr):**
- Machine events show: `"Pod deletion successful"`
- Both `returnRequestTime` and `returnCompletionTime` present
- Phase: `Completed`

**Example:**
```yaml
machineEvents:
  pod-0:
    message: Pod deletion successful
    returnCompletionTime: "2025-07-10T21:30:44.732648+00:00"
    returnRequestTime: "2025-07-10T21:30:44.204920+00:00"
    status: Completed
```

**What's happening:** Pods were gracefully terminated through normal return process.

**Action:** No action needed. Normal cleanup completed successfully.

## <a id="troubleshooting-commands"></a>Troubleshooting Commands

### <a id="check-resource-status"></a>Check Resource Status
```bash
# List all GCPSymphonyResources
kubectl get gcpsr -n gcp-symphony

# Get detailed status
kubectl get gcpsr <resource-name> -n gcp-symphony -o yaml

# List all MachineReturnRequests
kubectl get mrr -n gcp-symphony

# Check recent events
kubectl get events -n gcp-symphony --sort-by='.lastTimestamp'
```

### <a id="monitor-resource-lifecycle"></a>Monitor Resource Lifecycle
```bash
# Watch GCPSR changes
kubectl get gcpsr -n gcp-symphony -w

# Check pod status
kubectl get pods -n gcp-symphony -l symphony.requestId=<request-id>
```

## <a id="common-issues"></a>Common Issues and Solutions

### <a id="stuck-in-pending-phase"></a>Stuck in Pending Phase
**Symptoms:** Phase remains `Pending` or no Status is set, `availableMachines` not increasing
**Causes:**
- Insufficient node capacity
- Image pull failures
- Resource quota limits

**Investigation:**
```bash
kubectl describe pods -n gcp-symphony -l symphony.requestId=<request-id>
kubectl get nodes -o wide
```

**Notes**
Pods may show up as `Pending`. Typically this occurs when the kubernetes cluster needs to scale up and is taking longer time than expected. Monitor the nodes to ensure the control plane is able to scale out.

### <a id="pods-not-returning"></a>Pods Not Returning
**Symptoms:** MRR created but `returnedMachines` not increasing
**Causes:**
- Pods stuck in terminating state
- Node connectivity issues

**Investigation:**
```bash
kubectl get pods -n gcp-symphony --field-selector=status.phase=Terminating
kubectl describe mrr <mrr-name> -n gcp-symphony
```

### <a id="high-failed-machine-count"></a>High Failed Machine Count
**Symptoms:** `failedMachines` > 0 in MRR status
**Causes:**
- Pod deletion timeouts
- Node unavailability

**Investigation:**
- Check `machineEvents` in MRR status for specific error messages.
- Check for node failure events or control plane performace issues.


### <a id="pods-not-deleting"></a>Pods Not deleting
**Symptoms:** Deleted pods are stuck ub a terminating or error state
**Causes:**
- The control plane or operator is overwhelmed and is suffering from timeouts or API throttling
- The parent GCPSR was manually deleted

**Investigation:**
- Check to see if the parent GCPSymphonyResource is still available and not in `WaitingCleanup` state.
- Check the operator logs for the creation of a MachineReturnRequest for the pod(s) in question.

**Action:**
- If the gcpsr is still available and not in a `WaitingCleanup` state, continue to monitor the gcpsr for continued activity.
- If the gcpsr is still available and in a `WaitingCleanup` state, get the details and review the `returnedMachines` events. If all machines show successfully returned with a returnTime more than an hour old, there may be a problem with the cluster that needs to be reviewd and corrected.
- If the pods' parent gcpsr is no longer on the system, manual intervention will be necessary to remove them.
  - Check for and remove the operator's finalizer from the pod(s) in question:
    ```bash
    kubectl get pods -n gcp-symphony -l symphony.requestId=<request-id> -o yaml
    ```
    ```bash
      metadata:
      ...
        finalizers:                                                                                                        │
        - symphony-operator/finalizer
    ```
  - The following patch command can be used to remove the finalizer from all pod(s) associated with the same request-id:
    ```bash
    kubectl patch pod -n gcp-symphony -l symphony.requestId=<request-id> --type json -p '[{"op": "remove", "path": "/metadata/finalizers", "value": "symphony-operator/finalizer"}]'
    ```

### <a id="gcpsr-waiting-cleanup"></a>GCPSymphonyResource in `WaitingCleanup` state for longer than the `CRD_COMPLETED_RETAIN_TIME`
**Symptons:** A GCPSymphonyResource object does not get cleaned up by the operator's cleanup process.  
By default the cleanup process will remove any gcpsr or MachineReturnRequest (mrr|rrm) objects after they have reached `WaitingCleanup` and `Completed` state, respectively, for more than 24 hours. If they remain around longer than the `CRD_COMPLETED_RETAIN_TIME` + `CRD_COMPLETED_CHECK_INTERVAL`, the gcpsr may be missing a `Completed` condition with a status of `True`. This sometimes can happen during Node failures or very high control-plane activity where the completed events get lost to the operator.

**Investigation:**
Review the details of the GCPSymphonyResource in question:
```bash
kubectl get gcpsr <gcpsr-name> -o yaml
```
Review the conditions for one of type `Completed` with a status of `True`:
```yaml
  status:
    availableMachines: 0
    conditions:
    - lastTransitionTime: "2025-04-14T14:22:40.855099+00:00"
      message: GCPSymphonyResource g555dc430-f1a3-46bb-8b69-5c4c481abc25-2pzvc has
        no pods.
      reason: NoPods
      status: "True"        # This condition will ensure this
      type: Completed       # custom resource is cleaned up by the operator
    phase: WaitingCleanup
    returnedMachines:
    - name: g555dc430-f1a3-46bb-8b69-5c4c481abc25-2pzvc-pod-0
      returnRequestId: 7fd6805f-9a00-41f9-afe9-c38aa35002db
      returnTime: "2025-04-14T14:22:39.373216+00:00"
```
If this condition is not seen on the GCPSymphonyResource details, but the `phase: WaitingCleanup` does, the `Completed` event has been lost.

**Action:**
Check for any pods that are associated with this gcpsr.
```bash
kubectl get pods -l symphony.requestId=<request-id>
```
If any pods still exist, be sure to take note of the requestId.  If no pods exist, the gcpsr can safely be deleted with no further action:
```bash
kubectl delete gcpsr <gcpsr-name>
```
If pods existed prior to deleting the gcpsr, make sure that they are deleted when the gcpsr is deleted with the same `kubectl` command above. If they still exist, follow the action for [**Pods not deleting**](#pods-not-deleting) above.
