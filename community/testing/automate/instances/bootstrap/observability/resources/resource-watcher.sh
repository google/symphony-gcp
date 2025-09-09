#!/bin/env bash

# Escape everything but this...
export EGO_TOP=$EGO_TOP

echo "Sourcing profile.plaftrom"
source \$EGO_TOP/profile.platform

set -eo pipefail
echo "Logging in as Admin"
egosh user logon -u Admin -x Admin

# Create output directory if it does not exist
DATA_DIR=\$HF_TOP/log/resources
mkdir -p \$DATA_DIR

# Query hosts and current timestamp
data="\$(egosh resource list -ll -o status,ncpus,mem)"
timestamp=\$(date +%s)
echo "Queried first data at \$timestamp..."

# Write to new file with timestamp as name
printf "%s\n" "\$data" > \$DATA_DIR/\$timestamp

# Do this forever, if data differs, each 5 seconds.
while true; do
    new_data=\$(egosh resource list -ll -o status,ncpus,mem)
    timestamp=\$(date +%s)
    if [[ "\$data" != "\$new_data" ]]; then
        echo "Detected data change at \$timestamp..."
        data="\$new_data"
        printf "%s\n" "\$data" > \$DATA_DIR/\$timestamp
    fi
    sleep 5
done
