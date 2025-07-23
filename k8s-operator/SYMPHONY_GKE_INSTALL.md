# GCP GKE Operator Installation
Installing the GCP GKE Operator generally follows the standard kubernetes custom resource install process

* [Acquire the Operator image](#acquire-the-operator-image)
* [Configure the Operator manifests](#configure-the-operator-manifests)
* [Apply the Operator manifests](#apply-the-operator-manifests)

[Return to the Google Symphony Hostfactory main readme](../README.md)

# Acquire the Operator image
The operator image serves two primary purposes:
* Generate the kubernetes manifests needed to deploy the operator CRD
* The image supporting the Operator CRD's custom object

## Pull from FIXME image repository
GCP GKE Operator images can be pulled from [FIXME image repo](https://<FIXME>)

## Build from source

Example image build script
```
export IMAGE="gcp-symphony-operator"
export REGISTRY="<CHANGEME-image repo>"
export TAG="CHANGEME-0.0.0>"

bash -c 'docker buildx build --platform linux/amd64 -t $IMAGE:$TAG -t $IMAGE:latest -t $REGISTRY/$IMAGE:$TAG -t $REGISTRY/$IMAGE:latest .'
bash -c 'docker push $REGISTRY/$IMAGE:$TAG && docker push $REGISTRY/$IMAGE:latest'
```

# Configure the Operator manifests
> In the end, the resulting manifests will need to be applied to the kubernetes cluster, typicaly via `kubectl` or an IAC tool, so take that into consideration when choosing where/how to generate/modify the manifests.

## Generate the manifests
Use the `export-manifests` command with the operator image to generate a generic set of required kubernetes manifests.


```
docker run --rm  gcp-symphony-operator:latest export-manifests > /place/to/save/the/operator/manifests.yaml
```


## Modify the manifests
The `image: gcp-symphony-operator:latest` line in the generated `/place/to/save/the/operator/manifests.yaml` file is generally the only line that needs to be modified. Map the `image` value to the operator image name kuberenetes should pull. This would generally be assumed to be same image value used to generate the operator manifests.

The `imagePullPolicy: IfNotPresent` line is a second line that may warrant modification to align with the kubernetes cluster management practices.

# Apply the Operator manifests
Using the appropriate kuberenetes management tool, apply the configured operator manifests to the kubernetes cluster.

## kubectl
```
kubectl apply -f /place/to/save/the/operator/manifests.yaml
```

## Cluster Toolkit
If your GKE infrastructure is managed via Cluster Toolkit, add a `modules/management/kubectl-apply` source to the GKE blueprint, sourcing the configured manifests.

This example assumes the modified `/place/to/save/the/operator/manifests.yaml` has been copied to the same directory as the GKE blueprint:
```
  - id: symphony_operator_install
    source: modules/management/kubectl-apply
    use: [gke_cluster]
    settings:
      apply_manifests:
        - source: $(ghpc_stage("manifests.yaml"))
```
