# ================================= Auxiliary Function =================================

# Function to run commands as egoadmin with sourced environment...
run_as_egoadmin() {
    # sudo -u egoadmin bash -c "source \"$EGO_TOP/profile.platform\" && $*"
    su egoadmin -c "bash -c 'source $EGO_TOP/profile.platform && $*'"
}

# Function to check cluster is up by logon...
wait_for_cluster_start() {
    local max_attempts=30
    local attempt=1
    while ! run_as_egoadmin "egosh user logon -u \"$EGO_ADMIN_USERNAME\" -x \"$EGO_ADMIN_PASSWORD\"" >/dev/null 2>&1; do
        if ((attempt >= max_attempts)); then
            echo "Cluster failed to start after $max_attempts attempts"
            return 1
        fi
        echo "Cluster not started ... (attempt $attempt/$max_attempts)"
        sleep 4s
        ((attempt++))
    done
    return 0
}

create_cluster_admin () {
    # NOTE: In fact, since the SSH key is added via metadata keys
    # google automatically creates the user and adds it to the google-sudoers group
    # which is group 1000 by default.

    set -o pipefail

    INPUT_VARIABLES=(CLUSTERADMIN CLUSTER_ADMIN_GID CLUSTER_ADMIN_UID)
    check_all_set "${INPUT_VARIABLES[@]}"

    # Check if the cluster admin user exists, if not, create one
    echo "Checking if user $CLUSTERADMIN exists"
    if ! id -u "$CLUSTERADMIN" >/dev/null 2>&1; then
        echo "Creating $CLUSTERADMIN user"


        # Create user, update password and add it to the sudoers group
        groupadd -g $CLUSTER_ADMIN_GID $CLUSTERADMIN && \
        useradd $CLUSTERADMIN -u $CLUSTER_ADMIN_GID -g $CLUSTER_ADMIN_UID && echo "$CLUSTERADMIN:Admin" | chpasswd && \
        
        echo "$CLUSTERADMIN ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers.d/symphony-cluster-admins

        if [ $? -ne 0 ]; then
            echo "Cannot create user $CLUSTERADMIN, aborting..."
            exit 1
        fi
    else
        echo "User exists. Checking $CLUSTERADMIN UID and GID..."
        patch_uid_gid
    fi
}

patch_uid_gid () {
    INPUT_VARIABLES=(CLUSTERADMIN CLUSTER_ADMIN_GID CLUSTER_ADMIN_UID)
    check_all_set "${INPUT_VARIABLES[@]}"

    cat <<EOF
Patching clusteradmin UID/GID...
This is not a good solution but it is currently the only solution found for using a custom NFS server.
This may not be required when using a GCP NFS server or local Symphony deployments.
EOF
    CURRENT_GID=$(id -g $CLUSTERADMIN)
    if [[ $CURRENT_GID != $CLUSTER_ADMIN_GID ]]; then
        echo "Wrong GID ($CURRENT_GID)... Changing to $CLUSTER_ADMIN_GID."
        if ! groupmod -g $CLUSTER_ADMIN_GID $CLUSTERADMIN; then
            echo "Failed to modify group. Exiting..."
            exit 1
        fi

        echo "Modified GID. Pray that there are not many files with the wrong GID... Recursivelly modifying owner GID..."
        find / -gid $CURRENT_GID -exec chgrp -f $CLUSTER_ADMIN_GID '{}' \; 2>/dev/null
    fi
    CURRENT_UID=$(id -u $CLUSTERADMIN)
    if [[ $CURRENT_UID != $CLUSTER_ADMIN_UID ]]; then
        echo "Wrong UID ($CURRENT_UID)... Changing to $CLUSTER_ADMIN_UID."
        if ! usermod -g $CLUSTER_ADMIN_GID -u $CLUSTER_ADMIN_UID $CLUSTERADMIN; then
            echo "Failed to modify user. Exiting..."
            exit 1
        fi
        echo "Modified UID. Pray that there are not many files with the wrong UID... Recursivelly modifying owner UID..."
        find / -uid $CURRENT_GID -exec chown -h -f $CLUSTER_ADMIN_UID '{}' \; 2>/dev/null
    fi
}

install_symphony_dependencies () {
    DEPENDENCIES=(
        bc gettext bind-utils ed net-tools libnsl libcurl openssl ed dejavu-serif-fonts
        jq # required for RHEL7
        zip # required for patch install
        )
    if [[ $SHARED_FS_INSTALL == "Y" ]]; then
        DEPENDENCIES+=(rpc.statd) # NFSv3
        # DEPENDENCIES+=rpc.idmapd # NFSv4
    fi
    # If RHEL7 then substitute libnsl for net-tools
    echo "Installing dependencies: ${DEPENDENCIES[@]}"
    yum install -y "${DEPENDENCIES[@]}"
    if [ $? -ne 0 ]; then
        echo "Dependency installation failed, exiting..."
        exit 1
    fi
}

wait_nfs_available () {
    set -o pipefail

    INPUT_VARIABLES=(NFS_IP)
    check_all_set "${INPUT_VARIABLES[@]}"

    while ! showmount $NFS_IP --exports >/dev/null 2>&1; do
        echo "Waiting for NFS to be available..."
        # TODO: Add timeout here... (using the timeout command!!!)
        echo "TODO: Add timeout here..."
        sleep 10
    done
}

mount_nfs () {
    set -o pipefail

    INPUT_VARIABLES=(MOUNT_POINT NFS_IP NFS_SHARE)
    check_all_set "${INPUT_VARIABLES[@]}"

    wait_nfs_available

    echo "Mounting Symphony fileshare..."
    # If directory does not exist, create it...
    if [ ! -d $MOUNT_POINT ]; then
        mkdir -p $MOUNT_POINT
    fi
    # Add mount point to /etc/fstab
    echo "$NFS_IP:$NFS_SHARE  $MOUNT_POINT nfs defaults,vers=3   0   0" | tee -a /etc/fstab >/dev/null
    # Reload units and mount
    systemctl daemon-reload && mount $MOUNT_POINT
    if [ $? -ne 0 ]; then
        echo "Failed to mount fileshare or to reload systemctl"
        exit 1
    else
        echo "Successfully mounted fileshare"
    fi
}

update_nfs () {
    set -o pipefail

    INPUT_VARIABLES=(MOUNT_POINT NFS_IP NFS_SHARE)
    check_all_set "${INPUT_VARIABLES[@]}"

    wait_nfs_available

    echo "Seaching for old NFS config..."
    if [ ! -d $MOUNT_POINT ]; then
        mkdir -p $MOUNT_POINT
    fi

    LAST_LINE=$(tail -n 1 /etc/fstab)

    if echo "$LAST_LINE" | grep -q -E '\s+nfs\s+'; then
        echo "NFS line found, updating..."
        sed -i '$d' /etc/fstab # Delete last line...
        echo "$NFS_IP:$NFS_SHARE  $MOUNT_POINT nfs defaults,vers=3   0   0" | tee -a /etc/fstab >/dev/null

        systemctl daemon-reload && mount $MOUNT_POINT

        if [ $? -ne 0 ]; then
            echo "Failed to mount fileshare or to reload systemctl"
            exit 1
        else
            echo "Successfully mounted fileshare"
        fi
    else   
        echo "Last line of /etc/fstab is not NFS. Quitting..."
        exit 1
    fi
}


install_symphony () {
    set -o pipefail

    INPUT_VARIABLES=(SYM_BIN CLUSTERADMIN EGO_TOP RPMDB_DIR)
    check_all_set "${INPUT_VARIABLES[@]}"

    if [ ! -f $SYM_BIN ]; then
        echo "$SYM_BIN binary not found, exiting..."
        exit 1
    fi

    if [[ $SHARED_FS_INSTALL == "Y" ]]; then
        [ ! -d $EGO_TOP ] && mkdir -p $EGO_TOP
        if ! is_child_of $MOUNT_POINT $EGO_TOP; then
            echo "EGO_TOP is not child of MOUNT_POINT"
            exit 1
        fi
        [ ! -d $SHARED_TOP ] && mkdir -p $SHARED_TOP
        if ! is_child_of $MOUNT_POINT $SHARED_TOP; then
            echo "SHARED_TOP is not child of MOUNT_POINT"
            exit 1
        fi
        [ ! -d $RPMDB_DIR ] && mkdir -p $SHARED_TOP
        if ! is_child_of $MOUNT_POINT $RPMDB_DIR; then
            echo "RPMDB_DIR is not child of MOUNT_POINT"
            exit 1
        fi
    fi
    
    # Enable the egoadmin user to read the entitlement file
    chown -R $CLUSTERADMIN:$ROOT $(dirname "${SYM_BIN}")

    # Enable binary execution
    chmod u+x $SYM_BIN

    echo "Installing Symphony..."
    if ! sudo -E $SYM_BIN --prefix $EGO_TOP --dbpath $RPMDB_DIR --quiet; then
        echo "Symphony installation failed"
        exit 1
    fi
}

update_profile () {
    INPUT_VARIABLES=(CLUSTERADMIN EGO_TOP)
    check_all_set "${INPUT_VARIABLES[@]}"

    # For easier debugging...
    echo "export EGO_TOP=$EGO_TOP" | sudo tee -a /home/$CLUSTERADMIN/.bashrc >/dev/null
    echo "source $EGO_TOP/profile.platform" | sudo tee -a /home/$CLUSTERADMIN/.bashrc >/dev/null
    echo 'alias k="kubectl -n gcp-symphony"' | sudo tee -a /home/$CLUSTERADMIN/.bashrc >/dev/null
    echo "export EGO_TOP=$EGO_TOP" | sudo tee -a /etc/profile.d/egovars.sh >/dev/null 2>&1
}

wait_for_install_lock () {
    INPUT_VARIABLES=(SHARED_TOP)
    check_all_set "${INPUT_VARIABLES[@]}"
    # If shared environment and not primary host, then wait for finished installation...
    while [ ! -f $SHARED_TOP/startup.lock ]; do
        sleep 60
        # TODO: Add timeout here... (using the timeout command!!!)
        echo "Waiting for primary host setup..."
        echo "TODO: Add timeout here..."
    done
}

setup_sudoers_bashrc () {
    INPUT_VARIABLES=(EGO_TOP)
    check_all_set "${INPUT_VARIABLES[@]}"
    
    echo "Setting permissions and autostartup..."
    source $EGO_TOP/profile.platform
    sudo --preserve-env=EGO_TOP bash -c 'source $EGO_TOP/profile.platform && egosetsudoers.sh && egosetrc.sh' \
        && source $EGO_TOP/profile.platform

    if [ $? -ne 0 ]; then
        echo "Failed to run egosetsudoers.sh or egosetrc.sh"
        exit 1
    fi
}

check_required_vars () {
    INPUT_VARIABLES=(
        # Auxiliary variables required for installation
        EGO_TOP
        EGO_ADMIN_USERNAME
        EGO_ADMIN_PASSWORD
        SYM_BIN
        SYM_ENTITLEMENT
        CLUSTER_ADMIN_UID
        CLUSTER_ADMIN_GID
        SUCCESS_TAG
        FAIL_TAG

        # Required because we set use these variables during config.
        CLUSTERADMIN
        BASEPORT
        CLUSTERNAME

        # Static variable
        IBM_SPECTRUM_SYMPHONY_LICENSE_ACCEPT
    )

    # Additional input varables required if shared fs
    if [[ $SHARED_FS_INSTALL == "Y" ]]; then
        # Extract template NFS IP and share name
        INPUT_VARIABLES+=(
            NFS_IP # Required if shared fs
            NFS_SHARE # Required if shared fs
            MOUNT_POINT
            SHARED_TOP
            RPMDB_DIR
        )

    else
        INPUT_VARIABLES+=(
            PRIMARY_HOSTNAME # Required if not shared fs
        )
    fi

    if ! check_all_set "${INPUT_VARIABLES[@]}"; then
        exit 1
    fi
}

wait_clusteradmin () {
    echo "Waiting for creation of the user $CLUSTERADMIN..."
    while ! cat /etc/passwd | grep $CLUSTERADMIN >/dev/null 2>&1; do
        if ((attempt >= max_attempts)); then
            echo "Failed to find $CLUSTERADMIN user after $max_attempts attempts"
            exit 1
        fi
        echo "$CLUSTERADMIN user not found... Waiting creation... (attempt $attempt/$max_attempts)"
        sleep 10s
        ((attempt++))
    done
}

wait_disable_google_guest_managed_accounts () {
    local max_attempts=30
    local attempt=1
    wait_clusteradmin
    sleep 10s
    disable_google_guest_managed_accounts
}

bootstrap_private_key () {
    INPUT_VARIABLES=(
        EGO_TOP
        EGO_ADMIN_USERNAME
    )
    check_all_set "${INPUT_VARIABLES[@]}"

    echo "Configuring Symphony SSH keys..."
    local TARGET_SUBPATH="wlp/usr/shared/resources/security/private.key"
    cat <<-EOF | tee -a $EGO_TOP/kernel/conf/ego.conf >/dev/null
EGO_RSH="ssh -i $EGO_TOP/$TARGET_SUBPATH -o StrictHostKeyChecking=no"
EOF
    # TODO: Unhardcode this secret name............
    ( gcloud secrets versions access latest --secret="egoadmin_private_key"; echo ) > $EGO_TOP/$TARGET_SUBPATH
    chown $CLUSTERADMIN:$CLUSTERADMIN $EGO_TOP/$TARGET_SUBPATH
    chmod 600 $EGO_TOP/$TARGET_SUBPATH

}

install_patch_601711 () {
    echo "Starting install patch 601711..."

    INPUT_VARIABLES=(
        EGO_TOP
        CLUSTERADMIN
        RPMDB_DIR
    )
    check_all_set "${INPUT_VARIABLES[@]}"

    export FIX_PATH=/opt/ibm/bin/sym-7.3.2.0_x86_64_build601711.tar.gz
    export SYM_732_FIX_GCS_PATH=gs://symphony_dev_2/symphony_binaries/sym-7.3.2.0_x86_64_build601711.tar.gz
    export EXTRACT_FIX_PATH=/opt/ibm/bin/sym-7.3.2.0_x86_64_build601711

    echo "Downloading and extracting patch 601711..."
    gcloud storage cp $SYM_732_FIX_GCS_PATH $FIX_PATH
    mkdir $EXTRACT_FIX_PATH
    tar -xf $FIX_PATH -C $EXTRACT_FIX_PATH

    # Make egoadmin able to read it...
    chown -R $CLUSTERADMIN:$ROOT $EXTRACT_FIX_PATH
    chmod u+r $EXTRACT_FIX_PATH/*
    chmod a+x $EXTRACT_FIX_PATH/*.sh

    cd $EXTRACT_FIX_PATH

    # -m for management, -c for compute...
    if [[ "${EGOCOMPUTEHOST}" == "Y" ]]; then
        echo "Installing patch 601711 for compute host..."
        run_as_egoadmin "$EXTRACT_FIX_PATH/sym-7.3.2.sh -c -i"
        source $EGO_TOP/profile.platform
        $EXTRACT_FIX_PATH/symrpm-7.3.2.sh -c -i $RPMDB_DIR
        rpm -e egojre-8.0.6.36-600793.x86_64 --dbpath $RPMDB_DIR --nodeps
    else # Management host
        echo "Installing patch 601711 for management host..."
        run_as_egoadmin "$EXTRACT_FIX_PATH/sym-7.3.2.sh -m -i"
        source $EGO_TOP/profile.platform
        $EXTRACT_FIX_PATH/symrpm-7.3.2.sh -m -i $RPMDB_DIR
        rm -rf $EGO_CONFDIR/../../gui/work/*
        rm -rf $EGO_TOP/gui/workarea/*
        rm -rf $EGO_TOP/kernel/rest/workarea/*
        # TODO: Remove old packages usin rpm
    fi

    rm -rf $EGO_TOP/patch/backup/*
    rm -rf $EXTRACT_FIX_PATH
    rm -f $FIX_PATH
    
    cd -

    unset FIX_PATH
    unset SYM_732_FIX_GCS_PATH
    unset EXTRACT_FIX_PATH
}