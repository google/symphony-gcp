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
            exit 1
        fi
    done 
}

check_root () {
    # Check if root
    echo "Checking if current user is root"
    if [[ $EUID -ne 0 ]]; then
        echo "Current user is not root, aborting"
        exit 1
    fi
}

add_compute_self_tag () {
    INPUT_VARIABLES=(TAG)
    check_all_set "${INPUT_VARIABLES[@]}"
    ZONE=$(curl -s -H "Metadata-Flavor: Google" \
        http://metadata.google.internal/computeMetadata/v1/instance/zone | awk -F/ '{print $NF}')
    INSTANCE=$(curl -s -H "Metadata-Flavor: Google" \
        http://metadata.google.internal/computeMetadata/v1/instance/name)
    gcloud compute instances add-tags $INSTANCE --zone "$ZONE" --tags=$TAG
}

create_new_admin_user () {
    set -o pipefail

    INPUT_VARIABLES=(NEW_USERNAME NEW_PWD NEW_GID NEW_UID)

    check_all_set "${INPUT_VARIABLES[@]}"

    # Check if the cluster admin user exists, if not, create one
    echo "Checking if $NEW_USERNAME exists"
    if ! id -u "$NEW_USERNAME" >/dev/null 2>&1; then
        echo "Creating $NEW_USERNAME user"

        # Create user, update password and add it to the sudoers group
        groupadd -g $NEW_GID $NEW_USERNAME && \
        useradd $NEW_USERNAME -u $NEW_GID -g $NEW_UID && echo "$NEW_USERNAME:$NEW_PWD" | chpasswd && \
        echo "$NEW_USERNAME ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers.d/symphony-cluster-admins

        if [ $? -ne 0 ]; then
            echo "Cannot create user $NEW_USERNAME, aborting"
            return 1
        fi
    fi
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

timeout_wait_for_tag () {
    INPUT_VARIABLES=(ZONE TARGET_VM TARGET_TAG TIMEOUT)
    check_all_set "${INPUT_VARIABLES[@]}"

    for variable in ${INPUT_VARIABLES[@]}; do
        export ${variable}
    done
    [ ! -z $FAIL_TAG ] && export FAIL_TAG

    export -f check_all_set
    export -f wait_for_tag

    echo "Waiting $TARGET_VM($ZONE) for $TIMEOUT for tag $TARGET_TAG. Fail tag ${FAIL_TAG:-UNSET}. )"

    timeout $TIMEOUT bash -c wait_for_tag
    RETURN_CODE=$?

    if [ $RETURN_CODE -ne 0 ]; then
        if [ $RETURN_CODE -eq 124 ]; then
            echo "Timeout. $TARGET_TAG tag not found in $TIMEOUT. Exiting."
            exit $RETURN_CODE
        elif [ $RETURN_CODE -eq 2 ]; then
            echo "Fail. Fail tag $FAIL_TAG found. Exiting."
            exit $RETURN_CODE
        else
            echo "Wait for tag unknown error ($RETURN_CODE). Exiting."
            exit $RETURN_CODE
        fi
    fi
    
    return $RETURN_CODE
}

disable_google_guest_managed_accounts () {
    echo "Disabling google-guest-manager account_daemon to avoid problems with GID and UID"
    sed -i 's/accounts_daemon = true/accounts_daemon = false/g' /etc/default/instance_configs.cfg
    systemctl restart google-guest-agent
}

inject_pub_key_str () {
    # $1 is a user
    # $2 is the string key
    USER_HOME=$(grep $1 /etc/passwd | cut -d: -f 6)

    if [[ ! -d $USER_HOME ]]; then
        echo "HOME for user $1 ($USER_HOME) is not a directory"
    fi

    if [[ ! -d $USER_HOME/.ssh ]]; then
        mkdir $USER_HOME/.ssh
    fi

    echo "Injecting SSH key into $USER_HOME/.ssh/authorized_keys"

    echo $2 | tee -a $USER_HOME/.ssh/authorized_keys > /dev/null 2>&1

    chown $1:$1 -R $USER_HOME/.ssh
    chmod 700 $USER_HOME/.ssh
    chmod 600 $USER_HOME/.ssh/authorized_keys
}

is_child_of() {
  local parent=$(realpath "$1")
  local child=$(realpath "$2")

  [[ "$child" == "$parent"* && "$child" != "$parent" ]]
}

read_self_metadata () {
    local META_TARGET=$1
    curl -s -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/instance/attributes/${META_TARGET}" 2>/dev/null
}

query_fqdn () {
    local SHORT_HOSTNAME=$1
    nslookup $SHORT_HOSTNAME 2>/dev/null | awk '/^Name:/ {print $2; exit}'
}

get_vm_tags_from_fqdn() {
    local fqdn=$1
    [[ $fqdn =~ ^([^.]+)\.([^.]+)\.c\.([^.]+)\.internal$ ]] && \
    gcloud compute instances describe "${BASH_REMATCH[1]}" \
      --zone="${BASH_REMATCH[2]}" \
      --project="${BASH_REMATCH[3]}" \
      --format="value(tags.items[])" 2>/dev/null
}

check_all_true_numeric() {
    local array=("$@")
    
    for element in "${array[@]}"; do
        if [[ "$element" -ne 1 ]]; then
            return 1
        fi
    done
    return 0
}