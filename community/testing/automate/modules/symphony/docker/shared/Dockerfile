FROM rockylinux:8

ENV CLUSTERADMIN="egoadmin"
ENV CLUSTERADMIN_PWD="Admin"
ENV CLUSTER_ADMIN_UID="10001"
ENV CLUSTER_ADMIN_GID="10001"

RUN <<EOF
DEPENDENCIES=( 
    bc
    gettext
    bind-utils
    net-tools
    libnsl
    openssl
    ed
    dejavu-serif-fonts
    findutils
    sudo
    vim
    iproute
    procps
    jq
) 

yum install -y "${DEPENDENCIES[@]}"
EOF

RUN groupadd -g $CLUSTER_ADMIN_GID $CLUSTERADMIN
RUN useradd egoadmin -u $CLUSTER_ADMIN_UID -g $CLUSTER_ADMIN_GID
RUN echo "$CLUSTERADMIN:$CLUSTERADMIN_PWD" | chpasswd
RUN echo "egoadmin ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers.d/symphony-cluster-admins

RUN <<'EOT'
cat <<'EOF' > /entrypoint.sh
#!/bin/bash 

set -e

if [[ -z "$EGO_TOP" || ! -d "$EGO_TOP" ]]; then
    echo "EGO_TOP variable is not set. Exiting..."
    exit 1
fi

source $EGO_TOP/profile.platform && egosetsudoers.sh -f 

exec su -s /bin/bash egoadmin -c "source $EGO_TOP/profile.platform; $*"
EOF
chmod +x ./entrypoint.sh
EOT

ENTRYPOINT ["/entrypoint.sh"]
CMD ["egosh", "ego", "start;", "tail", "-f", "\"$EGO_TOP\"/kernel/log/lim.log.$(hostname)"]

# 1) egoconfig join in boucle en fonction des master/management listées, de façon hardcodé, then check exit code (à verifier si reponds bien).
# 2) Alternativelly modify the ego.conf to update the EGO_MASTER_LIST and simply use egosh ego start
# 3) alias DNS (CNAME ?) to dinamically point to master URL (can be problematic given the mismatch of IP/hostname -> Symphony checks it)

# Additional: EGO_GET_CONF=LIM on ego.conf of the local compute node. 