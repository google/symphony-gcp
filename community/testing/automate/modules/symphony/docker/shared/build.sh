#!/bin/bash

docker buildx build --pull -t sym-shared-rocky8:latest .
# --rm -f "./Dockerfile" 