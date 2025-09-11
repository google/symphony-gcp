# select base image
ARG base_image=rocky9
FROM rockylinux:8.9.20231119 AS rocky8
FROM rockylinux:9.3.20231119 AS rocky9
FROM $base_image AS build
ARG sym_version=7.3.2

# install symphony dependencies
# diffutils and zip are for the patch...
RUN yum install -y \
	bc \
	gettext \
	bind-utils \
	net-tools \
	libnsl \
	openssl \
	ed \
	dejavu-serif-fonts \
	findutils \
	sudo \
	vim \
	zip \
	diffutils \
	iproute \
	procps \
	jq \
	glibc-locale-source \
	glibc-langpack-en \
	&& yum clean all && rm -rf /var/cache/yum

# setup system requirements
RUN useradd -G wheel -m egoadmin && echo egoadmin:Admin | chpasswd && echo "egoadmin ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers.d/symphony-cluster-admins
RUN touch /var/run/utmp && chmod 664 /var/run/utmp && chown root:utmp /var/run/utmp
RUN echo LC_ALL=en_US.UTF-8 > /etc/locale.conf && \
	LC_ALL=en_US.UTF-8 localedef -v -c -i en_US -f UTF-8 en_US.UTF-8 | true
# RUN sed -i -e "s|4096|unlimited|g" /etc/security/limits.d/20-nproc.conf && \
#	echo "egoadmin soft nproc  65536" >> /etc/security/limits.conf && \
#	echo "egoadmin hard nproc  65536" >> /etc/security/limits.conf && \
#	echo "egoadmin soft nofile 65536" >> /etc/security/limits.conf && \
#	echo "egoadmin hard nofile 65536" >> /etc/security/limits.conf


# install symphony
RUN mkdir -p /opt/ibm
ADD --chmod=770 --link install.bin /opt/ibm/install.bin
ENV EGO_TOP=/opt/ibm/symphony CLUSTERADMIN=egoadmin IBM_SPECTRUM_SYMPHONY_LICENSE_ACCEPT=Y EGOCOMPUTEHOST=Y BASEPORT=17869 SIMPLIFIEDWEM=N DISABLESSL=Y
RUN /opt/ibm/install.bin --prefix $EGO_TOP --quiet && rm /opt/ibm/install.bin

# ============================ 7.3.2 patch 601711 ============================
# TODO: There is reason to believe that this part can be optmized by using another build step...
# Furthermore, this could be optimized by simply separating the Dockerfiles...
COPY patch.tar.gz /opt/ibm/patch.tar.gz

RUN <<EOF

export FIX_NAME=patch
export FIX_PATH=/opt/ibm/${FIX_NAME}.tar.gz

if [ ${sym_version} = "7.3.1" ]; then
	rm -f $FIX_PATH
	unset FIX_PATH
	unset FIX_NAME
	exit 0
fi

export EXTRACT_FIX_PATH=/opt/ibm/${FIX_NAME}

mkdir -p $EXTRACT_FIX_PATH
chmod 770 $FIX_PATH
tar -xf $FIX_PATH -C $EXTRACT_FIX_PATH
chmod u+r $EXTRACT_FIX_PATH/*
chmod a+x $EXTRACT_FIX_PATH/*.sh

# The cd is actually required... If not the patch scripts bug...
cd $EXTRACT_FIX_PATH

su -s /bin/bash $CLUSTERADMIN -c "source $EGO_TOP/profile.platform && $EXTRACT_FIX_PATH/sym-7.3.2.sh -c -i"

source $EGO_TOP/profile.platform
$EXTRACT_FIX_PATH/symrpm-7.3.2.sh -c -i

cd -

rm -rf $EGO_TOP/patch/backup/*
rm -rf $EXTRACT_FIX_PATH
rm -f $FIX_PATH
# TODO: Use rpm to remove patched packages...

unset FIX_PATH
unset EXTRACT_FIX_PATH
EOF
# ============================ end 7.3.2 patch 601711 ============================

WORKDIR /opt/ibm/symphony

# patches from official image
RUN sed -i "s|BINARY_TYPE=\"fail\"|BINARY_TYPE=\"linux-x86_64\"|g" kernel/conf/profile.ego && \
	sed -i "s|BINARY_TYPE=\"fail\"|BINARY_TYPE=\"linux-x86_64\"|g" jre/profile.jre && \
	sed -i "s|BINARY_TYPE=\"fail\"|BINARY_TYPE=\"linux-x86_64\"|g" soam/conf/profile.soam && \
	sed -i -e "s|AUTOMATIC|MANUAL|g" eservice/esc/conf/services/wsg.xml && \
	sed -i -e "s|AUTOMATIC|MANUAL|g" eservice/esc/conf/services/named.xml && \
	sed -i -e "s|AUTOMATIC|MANUAL|g" eservice/esc/conf/services/rsa.xml && \
	sed -i -e "s|MANUAL|AUTOMATIC|g" eservice/esc/conf/services/symrest.xml

# optimize image size
RUN rm -rf \
	gui \
	explorer \
	nodejs \
	integration/Matlab \
	integration/elk \
	hostfactory/1.2/providerplugins/aws \
	hostfactory/1.2/providerplugins/azure \
	hostfactory/1.2/providerplugins/openshift \
	4.0/linux-x86_64/etc/ussd \
	eservice/esc/conf/services/ussd.xml \
	soam/${sym_version}/linux-x86_64/lib/*.so* \
	soam/${sym_version}/linux-x86_64/bin/*32 \
	4.0/linux-x86_64/lib/lib2vemkd.so \
	soam/${sym_version}/linux-x86_64/etc/sd \
	soam/${sym_version}/linux-x86_64/etc/ssm \
	soam/${sym_version}/linux-x86_64/etc/ssm.krbwrapper \
	soam/${sym_version}/linux-x86_64/etc/smcproxy \
	soam/${sym_version}/linux-x86_64/etc/symrest \
	soam/${sym_version}/linux-x86_64/lib64/libvem.so.3.8.0 \
	soam/${sym_version}/linux-x86_64/lib64/libvem.so.3.7.0 \
	is \
	perf \
	jre/*/linux-x86_64/docs \
	4.0/linux-x86_64/etc/vemkd \
	4.0/linux-x86_64/etc/egosc \
	4.0/linux-x86_64/etc/rs \
	4.0/linux-x86_64/etc/rsa \
	4.0/linux-x86_64/etc/wsm \
	4.0/linux-x86_64/etc/named \
	4.0/linux-x86_64/etc/wsgserver \
	4.0/linux-x86_64/bin/egoapplykey \
	4.0/linux-x86_64/bin/egogenkey

RUN find -type d -name activation | xargs rm -rf && \
	find -type d -name upgrade | xargs rm -rf && \
	find -type d -name uninstall | xargs rm -rf && \
	find -type f -name rpi\* | xargs rm -rf

RUN find soam/${sym_version}/linux-x86_64/lib64 -name \*.so\* ! -type l | xargs -L 1 basename | xargs -L 1 -I '{}' find 4.0/linux-x86_64/lib -name {} | xargs -L 1 -I '{}' ln -sf {} soam/7.3*/linux-x86_64/lib64

RUN find -type f -executable -size +100k -print0 | xargs -0 strip -s 2>/dev/null | true && \
	find -name '*.so' -size +100k -print0 | xargs -0 strip --strip-unneeded && \
	find -name '*.so.*' -size +100k -print0 | xargs -0 strip --strip-unneeded

# symphony settings
RUN echo "EGO_DYNAMIC_HOST_TIMEOUT=10m" >> kernel/conf/ego.conf && \
	echo "EGO_DYNAMIC_HOST_WAIT_TIME=1" >> kernel/conf/ego.conf && \
	echo "EGO_RESOURCE_UPDATE_INTERVAL=1" >> kernel/conf/ego.conf && \
	echo "EGO_ENABLE_RG_UPDATE_MEMBERSHIP=Y" >> kernel/conf/ego.conf && \
	echo "EGO_RG_UPDATE_MEMBERSHIP_INTERVAL=10" >> kernel/conf/ego.conf && \
	echo "EGO_DISABLE_ROOT_REX=Y" >> kernel/conf/ego.conf && \
	echo "EGO_ELIM_RUNAS_CLUSTER_ADMIN=Y" >> kernel/conf/ego.conf && \
	echo "EGO_LIM_IS_IN_CONTAINER=Y" >> kernel/conf/ego.conf && \
	echo "EGO_GET_CONF=LIM" >> kernel/conf/ego.conf

# ================= fake linux version =================
# RUN mv /usr/bin/uname /usr/bin/uname.ori
# COPY --chmod=755 <<'EOT' /usr/bin/uname
# #!/bin/sh
# /usr/bin/uname.ori "$@" | sed -e 's/6\.6[0-9+.]*/5.15.0-1083-gke/' | sed -e 's/SMP/#89-Ubuntu SMP/'
# EOT
# COPY <<'EOT' /opt/ibm/proc-version
# Linux version 5.15.0-1083-gke (buildd@lcy02-amd64-001) (gcc (Ubuntu 11.4.0-1ubuntu1~22.04) 11.4.0, GNU ld (GNU Binutils for Ubuntu) 2.38) #89-Ubuntu SMP Fri May 30 20:50:59 UTC 2025
# EOT
# =================  end fake linux version =================

# force single layer so that deleted files are not in final image
FROM scratch
COPY --from=build / /
WORKDIR /opt/ibm
ENV EGO_TOP=/opt/ibm/symphony CLUSTERADMIN=egoadmin IBM_SPECTRUM_SYMPHONY_LICENSE_ACCEPT=Y EGOCOMPUTEHOST=Y BASEPORT=17869 SIMPLIFIEDWEM=N DISABLESSL=Y

# entrypoint: setup environment, requires `capabilities: ["SYS_NICE"]`
COPY --chmod=755 <<'EOT' /opt/ibm/entrypoint.sh
#!/bin/sh
set -e
if [ -z $SYM_MASTER ] ; then echo "SYM_MASTER must be specified"; exit 1 ; fi
if [ -z $SYM_CLUSTER_NAME ] ; then echo "SYM_CLUSTER_NAME must be specified"; exit 1; fi
source $EGO_TOP/profile.platform && egosetsudoers.sh -f


# ================= fake linux version =================
# mount --bind /opt/ibm/proc-version /proc/version
# ================= end fake linux version =================

if [ -f $EGO_TOP/kernel/conf/ego.cluster.cluster1 ]; then
	mv $EGO_TOP/kernel/conf/ego.cluster.cluster1 $EGO_TOP/kernel/conf/ego.cluster.$SYM_CLUSTER_NAME
fi
if [ -f $EGO_TOP/kernel/conf/ego.shared ]; then
	sed -i -e "s|cluster1|$SYM_CLUSTER_NAME|g" $EGO_TOP/kernel/conf/ego.shared
fi
su -s /bin/bash egoadmin -c "source $EGO_TOP/profile.platform && egoconfig join $SYM_MASTER -f && egosh ego start && $*"
EOT

COPY --chmod=755 <<'EOT' /opt/ibm/tail.sh
#!/bin/sh
set -e
(
trap 'kill 0' EXIT
for log in lim elim.sa melim pem pim ; do
	tail -Fq $EGO_TOP/kernel/log/$log.log.$(hostname) 2>/dev/null | fgrep '' --line-buffered | sed -u -e "s/^/[$log] /" | fgrep '' --line-buffered &
done
wait
)
EOT


# egosh ego start
ENTRYPOINT ["/opt/ibm/entrypoint.sh"]
CMD ["/opt/ibm/tail.sh"]
