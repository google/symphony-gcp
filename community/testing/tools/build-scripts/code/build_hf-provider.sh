#!/bin/env bash

# On the hf-provider directory

uv python install $(cat .python-version)
uv build . 

TARGET_URL=https://$TF_VAR_python_registry_location-python.pkg.dev/$TF_VAR_project_id/$TF_VAR_python_registry

uv publish \
    --check-url=$TARGET_URL/simple \
    --publish-url=$TARGET_URL \
    -u oauth2accesstoken \
    -p $(gcloud auth print-access-token)
