#!/bin/bash

IMAGE=sym-shared-rocky8
VERSION=$(git rev-parse HEAD)

docker tag $IMAGE:latest $TF_VAR_docker_repository/$IMAGE:latest
docker push $TF_VAR_docker_repository/$IMAGE:latest