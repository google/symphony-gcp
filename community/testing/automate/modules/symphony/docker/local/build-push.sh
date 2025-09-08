#!/bin/sh
set -e
REMOTE=$DOCKER_repository
if [ -z $REMOTE ] ; then
	if [ -z $TF_VAR_docker_repository ] ; then
		REMOTE=us-central1-docker.pkg.dev/symphony-dev-2/hf-gcp-testing
	else
		REMOTE=$TF_VAR_docker_repository
	fi
fi
if [ -z $SYM ] ; then
	SYM=7.3.2
fi
if [ -z $OS ] ; then
	OS=rocky9
fi
install_src=sym-$SYM.0_x86_64.bin
install_dst=$(dirname $0)/sym-$SYM/install.bin
if [ ! -f $install ] ; then
	echo "no symphony installer found, downloading $install_src..."
	gcloud storage cp gs://symphony_dev_2/symphony_binaries/install_src $install_dst
fi
NAME=sym-compute
TAGGED=$NAME:$OS-$SYM
echo REMOTE = $REMOTE
echo SYM    = $SYM
echo OS     = $OS
echo NAME   = $NAME
echo TAGGED = $TAGGED
DOCKER_BUILDKIT=1 docker build $(dirname $0)/sym-$SYM -f $(dirname $0)/Dockerfile -t $TAGGED -t $REMOTE/$TAGGED --build-arg base_image=$OS --build-arg sym-version=$SYM
docker push $REMOTE/$TAGGED
