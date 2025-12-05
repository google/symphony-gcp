# Overview

The primary GCP GKE Operator Installation Documentation is now maintained in the dedicated docs folder.

See full documentation at:
- [SYMPHONY_GKE_INSTALL.md](../SYMPHONY_GKE_INSTALL.md)

## Legacy Documentation (Do Not Use)

**Stop reading here unless you specifically need legacy info.**

<details>
<summary>Click to expand (legacy documentation)</summary>

The following is crude instructions on setting up the GCP Symphony Hostfactory Operator and GCP Symphony Hostfactory API Service to run in a kubernetes cluster.

These instructions only go so far as deploying and starting up the two container images in the cluster. We still need to add information for setting up ingress controllers for routing traffic to the service API.

## Requirements

- Docker runtime and tools (I used docker buildx)  
- A running kubernetes cluster and a local config file already pointing to it  

If you try to run the services outside of the cluster and connect you'll need to set a number of environment variables and ensure you have a valid kubernetes config file. Future docs will outline all necessary for this type of operation.


## Quick and dirty deploy of the operator to kubernetes cluster


### Build the operator docker image

To build the operator image, change to the `k8s-operator` directory and execute `docker buildx build -t gcp-symphony-operator:0.1.0 .`
```
% docker buildx build -t gcp-symphony-operator:0.1.0 .
[+] Building 12.6s (15/15) FINISHED                                                                     docker:colima
 => [internal] load build definition from Dockerfile                                                             0.0s
 => => transferring dockerfile: 680B                                                                             0.0s
 => [internal] load metadata for docker.io/library/python:3.13-slim                                              0.6s
 => [auth] library/python:pull token for registry-1.docker.io                                                    0.0s
 => [internal] load .dockerignore                                                                                0.0s
 => => transferring context: 2B                                                                                  0.0s
 => [internal] load build context                                                                                0.1s
 => => transferring context: 334.35kB                                                                            0.1s
 => [builder 1/6] FROM docker.io/library/python:3.13-slim@sha256:60248ff36cf701fcb6729c085a879d81e4603f7f507345  2.4s
.....
 => [builder 2/6] WORKDIR /app                                                                                   0.2s
 => [builder 3/6] COPY pyproject.toml .                                                                          0.0s
 => [builder 4/6] COPY README.md .                                                                               0.0s
 => [builder 5/6] COPY src ./src                                                                                 0.0s
 => [builder 6/6] RUN pip install uv &&     uv build --wheel --out-dir=dist .                                    2.6s
 => [stage-1 3/5] COPY --from=builder /app/dist/*.whl /app/                                                      0.0s
 => [stage-1 4/5] RUN pip install --no-cache-dir /app/*.whl                                                      6.3s
 => [stage-1 5/5] COPY gcp_symphony_operator.run .                                                               0.0s
 => exporting to image                                                                                           0.3s
 => => exporting layers                                                                                          0.3s
 => => writing image sha256:ca3fbb9d889f84d8099e4da00527affbf66a39218c26296d172977b15ee02623                     0.0s
 => => naming to docker.io/library/gcp-symphony-operator:0.1.0
```
Tag the image with `latest`
```
docker tag gcp-symphony-operator:0.1.0 gcp-symphony-operator:latest
```

### Load the image to a registry or the cluster node(s)

Load the resulting image into your registry, or onto your kubernetes node.  Locally, in minukube, the following can be used.
```
minikube image load gcp-symphony-operator:latest
```

### Build the HF API container image
Change directories to the `hf-service` directory and execute the command `docker buildx build -t hf-service-api:0.1.0 .`.
```
% docker buildx build -t hf-service-api:0.1.0 .
[+] Building 7.0s (11/11) FINISHED                                                                      docker:colima
 => [internal] load build definition from Dockerfile                                                             0.0s
 => => transferring dockerfile: 412B                                                                             0.0s
 => [internal] load metadata for docker.io/library/python:3.11-slim                                              0.6s
 => [auth] library/python:pull token for registry-1.docker.io                                                    0.0s
 => [internal] load .dockerignore                                                                                0.0s
 => => transferring context: 2B                                                                                  0.0s
 => [1/5] FROM docker.io/library/python:3.11-slim@sha....
 ....
 => [internal] load build context                                                                                0.1s
 => => transferring context: 145.54kB                                                                            0.1s
 => [2/5] WORKDIR /app                                                                                           0.1s
 => [3/5] COPY requirements.txt .                                                                                0.0s
 => [4/5] RUN pip install --no-cache-dir -r requirements.txt                                                     4.9s
 => [5/5] COPY src ./src                                                                                         0.0s
 => exporting to image                                                                                           0.3s
 => => exporting layers                                                                                          0.3s
 => => writing image sha256:7bd0aa03751e0fe3a0bcf63fc87c2652cf1bcf963b855074b6ce945950a4b14d                     0.0s
 => => naming to docker.io/library/hf-service-api:0.1.0                                                          0.0s
```

Tag the new image with `latest`
```
docker tag hf-service-api:0.1.0 hf-service-api:latest
```

Load the container image to your registry or kubernetes node(s). For minikube, use the command:
```
minikube image load hf-service-api:latest
```

### Deploy the operator manifest
Switch to the `k8s-operator` directory and execute the following command `kubectl apply -f manifests/operator-deploy.yaml`  

This will deploy the following resources:  
- a namespace called `gcp-symphony`
- a service account called `gcp-symphony-operator-sa`
- a role and role binding for the service account
- a cluster role and cluster role binding for the service account
- the GCPSymphonyOperator custom resource definition
- the GCP Symphony Operator itself (into the above-noted namespace)

### deploy the hostfactory service api service
Switch to the `hf-service` directory and exeute the command `kubctl apply -f manifests/hf-service-api.yaml`  

This will deploy the following resources:  
- a service called `hf-service-api-service`
- the service-api itsef


### deploy an ingress resource for the hf-service-api
*If you're running minikube, be sure to enable the ingress addon with* `minikube addons enable ingress`*. If using another kubernetes cluster, refer to that software's availaility of an ingress controller, or check out [Ingress-NginxController](https://kubernetes.github.io/ingress-nginx/deploy/#local-testing).*

Switch to the `hf-service` directory and execute the command `kubectl apply -f manifests/hf-service-ingress.yaml`

This will deploy the ingress resource that will allow for mapping from the ingress controller to the hf-service-api resource deployed earlier.  

***NOTE***: If using minikube, After applying the `hf-service-ingress.yaml` manifest, you'll need to run `minikube tunnel` in a separate terminal session and keep it going until you're done with your work session.

## TBD - a more details ingress setup
*Need to setup ingress controller to route traffic to the hf-service-api-service service.*


## Sample API Rest calls
Within the `hf-servie/docs` directory there is the [sample_curl_requests.md](../../hf-service/docs/sample_curl_requests.md) markdown file.



[Back to HOME](../README.md)

</details>