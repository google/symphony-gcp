# ===== Wait for startup =====

check_all_set () {
    # Check that all input variables are set
    # To be used in the form:
    #   variables=(var1 var2)
    #   var1=example
    #   var2=
    #   check_all_set "${variables[@]}"
    local variables=("$@")

    for variable in ${variables[@]}; do
        if [[ -z "${!variable}" ]]; then
            echo "$variable is not set. Exiting..."
            return 1
        fi
    done 
}

wait_for_tag () {
    INPUT_VARIABLES=(ZONE TARGET_VM TARGET_TAG)
    check_all_set "${INPUT_VARIABLES[@]}"
    
    TAG_FOUND=0

    while [ $TAG_FOUND -eq 0 ]; do
        
        IFS=";" read -a VM_TAGS <<< $(gcloud compute instances describe $TARGET_VM --zone $ZONE --format="value(tags.items)") 

        for tag in ${VM_TAGS[@]}; do
            if [[ $tag == $TARGET_TAG ]]; then
                TAG_FOUND=1
                return 0
            fi
            if [[ $FAIL_TAG || $tag == $FAIL_TAG ]]; then
                return 2
            fi
        done

        echo "Waiting for startup script to finish..."
        sleep 60
    done
}

# ==== Auxiliary Variables ====

# TODO: Import common scripts ands use tags as input variables
# Startup tag
export TARGET_TAG=startup-done
export FAIL_TAG=startup-fail

export -f wait_for_tag
export -f check_all_set
export TARGET_VM=$MGMT_INSTANCE

timeout 3h bash -c wait_for_tag
RETURN_CODE=$?
if [ $RETURN_CODE -ne 0 ]; then
    if [ $RETURN_CODE -eq 124 ]; then
        echo "Startup timeout. Exiting."
    else
        echo "Unknown error ($RETURN_CODE). Exiting"
    fi
    exit $RETURN_CODE
fi

export TARGET_VM=$MGMT_INSTANCE
timeout 1m bash -c wait_for_tag
RETURN_CODE=$?
if [ $RETURN_CODE -ne 0 ]; then
    echo "Failed to find startup-done tag for compute instance ($RETURN_CODE)"
    exit $RETURN_CODE;
fi

export TARGET_VM=$MGMT_INSTANCE
timeout 1m bash -c wait_for_tag
RETURN_CODE=$?
if [ $RETURN_CODE -ne 0 ]; then
    echo "Failed to find startup-done tag for NFS instance ($RETURN_CODE)"
    exit $RETURN_CODE;
fi

# ===== Stop instances =====

gcloud compute instances stop $MGMT_INSTANCE $NFS_INSTANCE $COMPUTE_INSTANCE \
    --zone $ZONE 