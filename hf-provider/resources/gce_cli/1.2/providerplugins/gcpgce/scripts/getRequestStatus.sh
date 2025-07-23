#!/bin/sh
# This script:
#    - should be called as getRequestStatus -f input.json
#    - exit with 0 if calling succeed and result will be in the stdOut
#    - exit with 1 if calling failed and error message will be in the stdOut
#
#. ${EGO_TOP}/profile.platform

inJson=$2
scriptDir=`dirname $0`
homeDir="$(cd "$scriptDir" && cd .. && pwd)"

$homeDir/bin/hf-gce getRequestStatus -f $inJson
