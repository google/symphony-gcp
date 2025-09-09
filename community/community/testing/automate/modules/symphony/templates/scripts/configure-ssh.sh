#!/bin/bash

configure_egosh_ssh () {
    echo "Configuring SSH and generating new keyspair..."
    # Fail if any commands fail...
    set -eo pipefail

    if [ -z $EGO_CONFDIR ]; then
        echo "EGO_CONFDIR is not set, exiting..."
        return 1
    fi

    if [ -z $CLUSTERADMIN ]; then
        echo "CLUSTERADMIN is not set, exiting..."
        return 1
    fi

    if [[ $USER -ne $CLUSTERADMIN ]]; then
        echo "User is not CLUSTERADMIN, exiting..."
        return 1
    fi

    # TODO: Find a way to better propagate the SSH private key...

    # Update EGO_RSH for setting SSH as the remote backend
    echo "# Added automatically by TF startup script" >> $EGO_CONFDIR/ego.conf
    echo 'EGO_RSH="ssh -i $EGO_CONFDIR/cluster.key -oPasswordAuthentication=no -oStrictHostKeyChecking=no"' >> $EGO_CONFDIR/ego.conf

    # Generate new keypairs
    # TODO: Somehow this is giving permission denied...
    ssh-keygen -t ed25519 -f $EGO_CONFDIR/cluster.key -N ""
}

configure_egosh_ssh_authorized_keys () {
    echo "Configuring SSH authorized keys..."
    # Fail if any commands fail...

    if [ -z $EGO_CONFDIR ]; then
        echo "EGO_CONFDIR is not set, exiting..."
        return 1
    fi

    if [ -z $CLUSTERADMIN ]; then
        echo "CLUSTERADMIN is not set, exiting..."
        return 1
    fi
    
    if [[ $USER -ne $CLUSTERADMIN ]]; then
        echo "User is not CLUSTERADMIN, exiting..."
        return 1
    fi

    # Add it to known hosts
    if [ ! -d $HOME/.ssh ]; then
        mkdir -p $HOME/.ssh/
        chmod 700 $HOME/.ssh/authorized_keys
    fi

    if [ ! -f $HOME/.ssh/authorized_keys ]; then
        touch $HOME/.ssh/authorized_keys
        chmod 600 $HOME/.ssh/authorized_keys
    fi

    echo "# Added automatically by TF startup script" >> $HOME/.ssh/authorized_keys
    cat $EGO_CONFDIR/cluster.key.pub >> $HOME/.ssh/authorized_keys 

}



