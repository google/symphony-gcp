Use a variable file such as in [example.json](./matrix_samples/example.json) to specify the autoscaling node pools spec. 

Please note that the order of the node pools spec will impact the automatically created `ComputeClass` on the bootstrap project. The order is from higher to lower priority (i.e. node pool spec index 0 => highest priority)

This project also creates a base pool with machines which are not SPOT/preemptible in order to deploy the operator, as specified by the `local.base_pool` variable.

It spawns the clusters already preconfigured for usage with a compute class, as specificed by the `local.compute_class` value. Thus, to properly use this pool one is required to configure the workload with the compute class. 

Please note that this project segments the different active clusters by using terraform workspaces.