compute_join_nwk_cluster () {
    INPUT_VARIABLES=(PRIMARY_HOSTNAME)
    check_all_set "${INPUT_VARIABLES[@]}"
    
    TARGET_VM=$(echo $PRIMARY_HOSTNAME | cut -d . -f1)
    
    if [[ -z $TARGET_VM ]]; then
        echo "TARGET_VM not found... Quitting..."
        exit 1
    fi
    
    ZONE=$(echo $PRIMARY_HOSTNAME | cut -d . -f2)

    if [[ -z $ZONE ]]; then
        echo "ZONE not found... Quitting..."
        exit 1
    fi

    TARGET_TAG=$SUCCESS_TAG
    TIMEOUT=30m

    timeout_wait_for_tag 

    if ! run_as_egoadmin "yes | egoconfig join $PRIMARY_HOSTNAME"; then
        echo "Failed to join cluster"
        exit 1
    fi
}

preinstall_compute () {
    check_root
    create_cluster_admin
    install_symphony_dependencies
}

install_compute () {
    if [[ $SHARED_FS_INSTALL != "Y" ]]; then
        # Install on every machine on a non-shared environment...
        echo "Standard installation..."
        install_symphony
        source $EGO_TOP/profile.platform
        [[ "${SOAM_VERSION}" == "7.3.2" ]] && install_patch_601711
    else
        INPUT_VARIABLES=(NFS_IP NFS_SHARE)
        check_all_set "${INPUT_VARIABLES[@]}"
        mount_nfs
    fi
}

postinstall_compute () {
    update_profile

    if [[ $SHARED_FS_INSTALL != "Y" ]]; then
        echo "TODO: Find a way to properly wait for cluster startup..."
    else
        wait_for_install_lock
    fi

    setup_sudoers_bashrc
}

join_compute () {
    if [[ $SHARED_FS_INSTALL != "Y" ]]; then
        compute_join_nwk_cluster
        # NOTE: No need to do this on a shared environment. Only need to startup the host `egosh ego start`.
    fi
}

restore_compute () {
    if [[ $SHARED_FS_INSTALL == "Y" ]]; then
        update_nfs
    fi
    patch_uid_gid # Why oh why :( ??????
    postinstall_compute
    join_compute
    run_as_egoadmin "egosh ego start"
}