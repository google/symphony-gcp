#!/bin/env bash

# Get the script filename without extension 
SCRIPT_FILE=$(basename $0)
IFS="." read -ra SCRIPT <<< "$SCRIPT_FILE"
SCRIPT=${SCRIPT[0]}

inJson=$2
# TODO: Add intercept logic
hf-gke $SCRIPT -f $inJson