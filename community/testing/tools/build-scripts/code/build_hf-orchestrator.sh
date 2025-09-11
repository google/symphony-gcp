#!/bin/bash

# On the k8s-operator directory

gcloud auth configure-docker $TF_VAR_docker_registry_location-docker.pkg.dev --quiet

docker buildx build . --tag $TF_VAR_docker_repository/k8s-operator:latest --push