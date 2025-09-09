update_vm_max_map_count () {
    # Add vm.max_map_count for ELK stack
    # MANAGEMENT HOST ONLY
    tee -a /etc/sysctl.conf >/dev/null <<EOF
# Symphony - ELK configuration
vm.max_map_count=262144
EOF
    sysctl -p 
}

update_security_limits () {
    # Setup the limits for the number of processes and files open.
    # MANAGEMENT HOST ONLY

    if [ -z $CLUSTERADMIN ]; then
        echo "CLUSTERADMIN is not set, exiting..."
        exit 1
    fi

    # Get the root user name
    ROOT=$(getent passwd 0 | cut -d: -f1)

    # Create the limits file
    cat <<EOF > /etc/security/limits.d/$CLUSTERADMIN.limits.conf
$CLUSTERADMIN soft nproc 65536
$CLUSTERADMIN hard nproc 65536
$CLUSTERADMIN soft nofile 65536
$CLUSTERADMIN hard nofile 65536
$ROOT soft nproc 65536
$ROOT hard nproc 65536
$ROOT soft nofile 65536
$ROOT hard nofile 65536
EOF
}

update_sysctl_config () {
    cat <<EOF >> /etc/sysctl.conf
# ======= Symphony large scale optimization =======
# Allows reusing sockets in the TIME_WAIT state, for new connections when it is safe from the protocol viewpoint.
# The default value is 0 (disabled). 
# This parameter is generally a safer alternative than configuring the tcp_tw_recycle parameter.
net.ipv4.tcp_tw_reuse = 1

# Enables fast recycling of TIME_WAIT sockets. 
# The default value is 0 (disabled).
# Use with caution when working with load balancers.
# Note that the tcp_tw_recycle parameter is particularly useful in environments where numerous short connections are open and left in TIME_WAIT state,
# such as Web servers and load balancers. Reusing the sockets can be very effective in reducing server load.
# DEVELOPPER NOTE: This actually might not work on GCP. 
# net.ipv4.tcp_tw_recycle = 1

# Determines the time that must elapse before TCP/IP can release a closed connection and reuse its resources. 
# During this TIME_WAIT state, reopening the connection to the client costs less than establishing a new connection. 
# By reducing the value of this entry, TCP/IP can release closed connections faster, making more resources available for new connections.
net.ipv4.tcp_fin_timeout = 30

# The maximum number of unique process identifiers your system can support, from the kernel side. 
# We used this setting to increase the maximum supported process identifiers for the system.
kernel.pid_max = 65535

# Defines the number of possible active connections that the system can issue to other systems that do not support the TCP extension timestamps. 
# We used this setting to ensure the system could afford a large number of TCP connections.
net.ipv4.ip_local_port_range = 1024    65535

# Determines the values of four semaphore parameters:
# SEMMSL: maximum number of semaphores per array
# SEMMNS: maximum semaphores system-wide
# SEMOPM: maximum operations per semop call
# SEMMNI: maximum arrays
# We mainly used this parameter to increase the system semaphores, to avoid multi-thread- or recursive-related issues, as these features frequently consume more semaphores.
kernel.sem =5010 641280 5010 12800

# Limits the socket listen() backlog, known in the user space as SOMAXCONN. 
# The default is 128. The value should be raised substantially to support bursts of requests. 
# We mainly used this parameter to avoid the system rejecting bursts of requests.
net.core.somaxconn = 65536

# Increases the number of incoming connections in the backlog queue. 
# Also sets the maximum number of packets, queued on the input side, when the interface receives packets faster than the kernel can process.
net.core.netdev_max_backlog = 65536

# The maximum number of connection requests, that the system has in memory, which have not yet received acknowledgment from the connecting client.
net.ipv4.tcp_max_syn_backlog = 40000

# to increase the TCP maximum buffer size set using setsockopt()
# net.core.rmem_max=16777216
# net.core.wmem_max=16777216
# net.core.rmem_default=5000000
# net.core.wmem_default=5000000

# DEVELOPPER NOTE: Let's be more conservative
net.core.rmem_default=87380      # Linux default (~85KB)
net.core.wmem_default=16384      # Linux default (16KB)
net.core.rmem_max=16777216       # Allow tuning up when needed
net.core.wmem_max=16777216       # Allow tuning up when needed

# To increase the threshold levels for ARP cache on-the-fly.
# net.ipv4.neigh.default.gc_thresh1 = 8192
# net.ipv4.neigh.default.gc_thresh2 = 8192    
# net.ipv4.neigh.default.gc_thresh3 = 8192

# Specifies how often to send TCP keepalive packets to keep a connection alive if it is currently unused.
net.ipv4.tcp_keepalive_time=120

# The number of TCP keepalive probes to send out before the system decides that a specific connection is broken.
net.ipv4.tcp_keepalive_probes=2

# The amount of time to wait for a reply for each keepalive probe.
net.ipv4.tcp_keepalive_intvl=15

# Increases Linux automatic tuning of TCP buffer limits to use (minimum, default, and maximum number of bytes).
# Set the maximum to 16 MB for 1 GE, and 32 M or 54 M for 10 GE
net.ipv4.tcp_wmem=4096 65536 16777216     

EOF

    sysctl -p 
}

update_ego_config () {
    cat <<EOF >> $EGO_CONFDIR/ego.conf
# ======= Symphony large scale optimization =======
# Improves VEMKD file operation performance, thereby improving client response time and overall cluster performance.
EGO_ENABLE_COMPRESS_STATUS_FILE=Y

# Specified in MB, reduces the frequency for VEMKD to switch the stream file, to give the reporting framework loader sufficient time to finish loading data from the file to the database. 
EGO_DATA_MAXSIZE=100

# Increases the number of connections EGO can maintain
EGO_MAX_CONN=20000

# Specified in bytes, controls the XDR buffer size during communication between master and slave LIMs.
# This needs to be modified accross all hosts to...
# Should be increased
EGO_MASTER_ANN_BUF_SIZE=40960 

# Defines the message queue chunk size for SSM. A large chunk size will lead SIM and SSM’s connection be rejected by the operating system’s security policy.
# SSM will flush all requests only when the message queue is NULL, or when the resource operation request size is equal or larger than the configured value. The default value is 100.
MAX_RESOURCE_OPERATION_CHUNK_SIZE=20

# Use this parameter to control SSM's request handling rate.
# If configured, after a batch or resource operation requests are sent, SSM will postpone the remaining resource operation requests for the configured interval.
# By default, there is no delay on sending resource operation requests.
RESOURCE_OPERATION_INTERVAL=1

# Time period for PEM to cache the unique identifier (UID) locally, to avoid container setup failure in large clusters due to NIS limitations.
EGO_UID_CACHE_DURATION=600
EOF
    sed -i "s/^EGO_DYNAMIC_HOST_WAIT_TIME=.*/# Modified for large scale optimization\nEGO_DYNAMIC_HOST_WAIT_TIME=600 /" $EGO_CONFDIR/ego.conf
}

update_cluster_config () {
    cat <<EOF >> $EGO_CONFDIR/ego.cluster.$CLUSTERNAME
# ======= Symphony large scale optimization =======
# Increases VEMKD’s chances to obtain load information from the master LIM.
EXINTERVAL=150
EOF
}

update_wsm_config () {
    cat <<EOF >> $EGO_CONFDIR/wsm.conf
# ======= Symphony large scale optimization =======
# Reduces the chance of the WEBGUI service restarting
# Helps PERF (the reporting framework) generate reports
# To use this parameter with a setting of 4096, 
# ensure that the management host running the WEBGUI service has sufficient memory (that is, more than 4096 MB).
# DEVELOPPER NOTE: This is already applied by default.
# MEM_HIGH_MARK=4096 
JAVA_OPTS="-Xms512m -Xmx4096m"
EOF
}

initialize_primary_node () {
    INPUT_VARIABLES=(EGO_ADMIN_PASSWORD SYM_ENTITLEMENT)
    check_all_set "${INPUT_VARIABLES[@]}"

    if [ ! -f $SYM_ENTITLEMENT ]; then
        echo "$SYM_ENTITLEMENT entitlement file not found"
    fi

    # Initialize the primary host...
    if ! run_as_egoadmin "yes | egoconfig join $(hostname -f)"; then
        echo "Failed to initialize primary host"
        exit 1
    fi

    # Skip this if Symphony != 7.3.2
    if [[ "${SOAM_VERSION}" == "7.3.2" ]]; then
        if ! run_as_egoadmin "yes | egoconfig setpassword -x $EGO_ADMIN_PASSWORD"; then
            echo "Failed to set cluster administrator password"
            exit 1
        fi
    fi
    
    if ! run_as_egoadmin "egoconfig setentitlement $SYM_ENTITLEMENT"; then
        echo "Failed to set cluster entitlement"
        exit 1
    fi
}

mgmt_join_shared_cluster () {
    INPUT_VARIABLES=(SHARED_TOP)
    check_all_set "${INPUT_VARIABLES[@]}"
    
    if ! run_as_egoadmin "yes | egoconfig mghost $SHARED_TOP"; then
        echo "Failed to join as management host"
        exit 1
    fi
}

preinstall_mgmt () {
    check_root
    create_cluster_admin
    # MANAGEMENT HOST ONLY
    # Add vm.max_map_count for ELK stack
    update_vm_max_map_count
    # Setup the limits for the number of processes and files open.
    update_security_limits

    install_symphony_dependencies
}

install_mgmt () {
    # Install...
    if [[ $SHARED_FS_INSTALL != "Y" ]]; then
        # Install on every machine on a non-shared environment...
        echo "Standard installation..."
        install_symphony
        source $EGO_TOP/profile.platform
        [[ "${SOAM_VERSION}" == "7.3.2" ]] && install_patch_601711
        bootstrap_plugin # Imported from plugin-template... 
        if [[ $PRIMARY_HOSTNAME == $(hostname -f) ]]; then
            echo "Primary host installation..."
            export IS_FIRST_INSTALL=1
        else
            export IS_FIRST_INSTALL=0
        fi
    else
        INPUT_VARIABLES=(NFS_IP NFS_SHARE)
        check_all_set "${INPUT_VARIABLES[@]}"
        mount_nfs

        if [ ! -d $SHARED_TOP ]; then
            mkdir -p $SHARED_TOP
        fi

        if ! ls $SHARED_TOP/first.lock >/dev/null 2>&1; then
            touch $SHARED_TOP/first.lock
            echo "First time installation..."
            export IS_FIRST_INSTALL=1
            install_symphony
            source $EGO_TOP/profile.platform
            [[ "${SOAM_VERSION}" == "7.3.2" ]] && install_patch_601711
            bootstrap_plugin # Imported from plugin-template... 
        else
            export IS_FIRST_INSTALL=0
        fi
    fi
}

postinstall_mgmt () {
    update_profile

    # If shared filesystem and first time installation...
    if [[ $SHARED_FS_INSTALL == "Y" && $IS_FIRST_INSTALL -eq 1 ]]; then
        bootstrap_private_key
    fi

    # If shared filesystem and not first time installation...
    if [[ $SHARED_FS_INSTALL == "Y" && $IS_FIRST_INSTALL -ne 1 ]]; then
        wait_for_install_lock
    fi

    setup_sudoers_bashrc
}

join_mgmt () {
    if [[ $IS_FIRST_INSTALL -eq 1 ]]; then
        echo "Initializing primary node..."
        initialize_primary_node
    else    
        echo "Joining existing cluster..."
        # If shared filesystem and not first time installation...
        if [[ $SHARED_FS_INSTALL == "Y" ]]; then
            mgmt_join_shared_cluster
        else
            if ! run_as_egoadmin "egoconfig join $PRIMARY_HOSTNAME -f"; then
                echo "Failed to join as management host"
                exit 1
            fi
        fi
    fi
}

setup_failover () {
    local secondary_hosts=()
    local secondary_hosts_fqdn=()
    local tags_found=()
    local tags=()
    
    # Read secondary hosts with error handling
    local secondary_failover
    local secondary_nodes
    if ! secondary_nodes=$(read_self_metadata "SECONDARY_NODES"); then
        echo "Error: Failed to read SECONDARY_NODES metadata" >&2
        return 1
    fi
    
    # Parse secondary hosts
    IFS="," read -ra secondary_hosts <<< "$secondary_nodes"
    
    if [[ ${#secondary_hosts[@]} -eq 0 ]]; then
        echo "No secondary hosts found... Considering single Master installation..."
        return 0
    fi
    
    # Resolve FQDNs for all secondary hosts
    echo "Resolving FQDNs for ${#secondary_hosts[@]} secondary hosts..."
    for secondary in "${secondary_hosts[@]}"; do
        local fqdn
        if fqdn=$(query_fqdn "$secondary"); then
            secondary_hosts_fqdn+=("$fqdn")
            echo "Resolved $secondary -> $fqdn"
        else
            echo "Error: Failed to resolve FQDN for $secondary" >&2
            return 1
        fi
    done
    
    # Validate TARGET_TAG is set
    if [[ -z "$SUCCESS_TAG" ]]; then
        echo "Error: SUCCESS_TAG is not set" >&2
        return 1
    fi
    
    echo "Waiting for all secondary hosts to have tag '$SUCCESS_TAG'..."
    
    # Main polling loop
    while true; do
        tags_found=()
        local all_success=true
        
        for secondary_fqdn in "${secondary_hosts_fqdn[@]}"; do
            echo "Checking $secondary_fqdn for tag '$SUCCESS_TAG'..."
            
            # Get VM tags with error handling
            local vm_tags_raw
            if vm_tags_raw=$(get_vm_tags_from_fqdn "$secondary_fqdn"); then
                IFS=";" read -ra tags <<< "$vm_tags_raw"
            else
                echo "Warning: Failed to get tags for $secondary_fqdn" >&2
                tags=()
            fi
            
            # Check if target tag exists
            local tag_found=false
            for tag in "${tags[@]}"; do
                if [[ "$tag" == "$SUCCESS_TAG" ]]; then
                    echo "✓ Tag '$SUCCESS_TAG' found on $secondary_fqdn"
                    tag_found=true
                    break
                fi
            done
            
            if [[ "$tag_found" == true ]]; then
                tags_found+=(1)
            else
                echo "✗ Tag '$SUCCESS_TAG' not found on $secondary_fqdn"
                tags_found+=(0)
                all_success=false
            fi
        done
        
        # Check if all hosts have the target tag
        if [[ "$all_success" == true ]] && check_all_true_numeric "${tags_found[@]}"; then
            echo "✓ All secondary hosts have the required tag. Starting failover setup..."
            break
        fi
        
        echo "Waiting 10 seconds before next check..."
        sleep 10
    done

    joined_fqdns="$(hostname -f),$(IFS=","; echo "${secondary_nodes[*]}")"
    echo "Setting master list to $joined_fqdns"

    run_as_egoadmin "egoconfig masterlist $joined_fqdns"
}

startup_mgmt () {
    echo "TODO: Merge with restore_mgmt code."
}

restore_mgmt () {
    if [[ $SHARED_FS_INSTALL == "Y" ]]; then
        update_nfs
        
        STARTUP_INDEX=$(read_self_metadata "STARTUP_INDEX")

        if [[ $STARTUP_INDEX -eq 0 ]]; then
            echo "Primary host restauration..."
            export IS_FIRST_INSTALL=1
        else
            export IS_FIRST_INSTALL=0
        fi
    else 
        if [[ $PRIMARY_HOSTNAME == $(hostname -f) ]]; then
            echo "Primary host restauration..."
            export IS_FIRST_INSTALL=1
        else
            export IS_FIRST_INSTALL=0
        fi
    fi
    
    patch_uid_gid # Why oh why :( ??????
    postinstall_mgmt
    join_mgmt
    if [[ $SHARED_FS_INSTALL == "Y" && $IS_FIRST_INSTALL -eq 1 ]]; then
        echo "Finished primary host configuration... Freeing-up lock..."
        touch $SHARED_TOP/startup.lock
        setup_failover
        run_as_egoadmin "yes | egosh ego start all"
        wait_for_cluster_start
    fi
}