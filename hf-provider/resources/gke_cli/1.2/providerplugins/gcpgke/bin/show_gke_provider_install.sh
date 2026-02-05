#!/bin/bash
SLEEP=1
PROVIDERPLUGINSDIRNAME=gcpgke
PROVIDERINSTANCEDIRNAME=gcpgkeinst
LOGFILE=/dev/null

function fail() {
  echo -e "\e[0;31mError: $1\e[0m" >&2 # Send message to stderr
}

# Function to display help/usage information
function usage() {
    cat <<EOT
Usage: $(basename "$0") [-h] [-l file] [-p dir_name] [-i dir_name] -- Validate provider plugin installation

where:
    -h             Show this help text
    -l <file>      Set the log file (default: ${LOGFILE})
    -p <dir name>  Set the provider plugin directory name (default: ${PROVIDERPLUGINSDIRNAME})
    -i <dir name>  Set the provider instance directory name (default: ${PROVIDERINSTANCEDIRNAME})
EOT
    exit 0
}

# Parse options using getopts
while getopts ':hl:p:i:' option; do
    case "$option" in
        h)  usage
            ;;
        l)  if [ -z "$OPTARG" -o "${OPTARG:0:1}" = "-" ] ; then
              printf "*** Missing argument for -l"  >&2
              echo ""
              usage >&2
            fi
            LOGFILE=$OPTARG
            ;;
        p)  if [ -z "$OPTARG" -o "${OPTARG:0:1}" = "-" ] ; then
              printf "*** Missing argument for -p"  >&2
              echo ""
              usage >&2
            fi
            PROVIDERPLUGINSDIRNAME=$OPTARG
            ;;
        i)  if [ -z "$OPTARG" -o "${OPTARG:0:1}" = "-" ] ; then
              printf "*** Missing argument for -i"  >&2
              echo ""
              usage >&2
            fi
            PROVIDERINSTANCEDIRNAME=$OPTARG
            ;;
        :)  # Handle missing arguments
            printf "*** Missing argument for -%s\n" "$OPTARG" >&2
            echo ""
            usage >&2
            ;;
        \?) # Handle invalid options
            printf "*** Invalid option: -%s\n" "$OPTARG" >&2
            echo ""
            usage >&2
            ;;
    esac
done

# Shift processed arguments so the main script can use remaining positional arguments
shift $((OPTIND - 1))

## Redirect stdout to a process substitution that runs tee
exec 1> >(tee -a "$LOGFILE")

## Redirect stderr to the same place as stdout
exec 2>&1

## Check prerequisites
if [[ -z ${HF_TOP} ]]
then
  echo "\$HF_TOP is empty. Please source your symphony environment (e.g. '. \$EGO_TOP/profile.platform')"
  exit 1
fi

if [[ -z $(which tree) ]]
then
  echo "'tree' not installed. 'dnf install tree' to install"
fi

## Zero out the log file
# shellcheck disable=SC2188
> "${LOGFILE}"

## Show install info

echo ''
echo -e "\033[1mConfirm the Symphony variables\033[0m"
echo "\$HF_TOP: ${HF_TOP}"
echo "\$HF_VERSION: ${HF_VERSION}"
echo ''

## HF_PROVIDER VALIDATION

echo ''
echo -e "\033[1mConfirm the provider plugin directory structure\033[0m"
sleep $SLEEP
echo "tree \$HF_TOP/\$HF_VERSION/providerplugins/${PROVIDERPLUGINSDIRNAME}"
tree "${HF_TOP}"/"${HF_VERSION}"/providerplugins/"${PROVIDERPLUGINSDIRNAME}" || fail "Check install"

echo ''
echo -e "\033[1mConfirm the provider plugin is present and enabled\033[0m"
sleep $SLEEP
echo "grep -A1 -B1 ${PROVIDERPLUGINSDIRNAME} \$HF_TOP/conf/providerplugins/hostProviderPlugins.json"
grep -A1 -B1 "${PROVIDERPLUGINSDIRNAME}" "${HF_TOP}"/conf/providerplugins/hostProviderPlugins.json || fail "Check install"

echo ''
echo -e "\033[1mChange to the provider instance directory\033[0m"
sleep $SLEEP
echo "cd \$HF_TOP/conf/providers/${PROVIDERINSTANCEDIRNAME}/"
cd "${HF_TOP}"/conf/providers/"${PROVIDERINSTANCEDIRNAME}"/ || fail "Check install"

echo ''
echo -e "\033[1mShow the provider instance ${PROVIDERINSTANCEDIRNAME}prov_config.json file\033[0m"
sleep $SLEEP
echo "cat ${PROVIDERINSTANCEDIRNAME}prov_config.json"
cat "${PROVIDERINSTANCEDIRNAME}"prov_config.json || fail "Check install"

# Extract the kubectl config file from ${PROVIDERINSTANCEDIRNAME}prov_config.json
KUBE_CONFIG=$(grep GKE_KUBECONFIG "${HF_TOP}"/conf/providers/"${PROVIDERINSTANCEDIRNAME}"/"${PROVIDERINSTANCEDIRNAME}"prov_config.json | awk -F\" '{print $4}')

echo ''
echo -e "\033[1mConfirm the GKE_KUBECONFIG file is present\033[0m"
sleep $SLEEP
echo "ls -l ${KUBE_CONFIG}"
ls -l "${KUBE_CONFIG}" || fail "Check install"

echo ''
echo -e "\033[1mConfirm the GKE_KUBECONFIG file is valid\033[0m"
sleep $SLEEP
echo "kubectl --kubeconfig=${KUBE_CONFIG} get nodes"
kubectl --kubeconfig="${KUBE_CONFIG}" get nodes || fail "Check install"

echo ''
echo -e "\033[1mShow the provider instance ${PROVIDERINSTANCEDIRNAME}prov_templates.json file\033[0m"
sleep $SLEEP
echo "cat ${PROVIDERINSTANCEDIRNAME}prov_templates.json"
cat "${PROVIDERINSTANCEDIRNAME}"prov_templates.json || fail "Check install"

# Extract the podspec yaml file from ${PROVIDERINSTANCEDIRNAME}prov_template.json
PODSPEC=$(grep podSpecYaml "${HF_TOP}"/conf/providers/"${PROVIDERINSTANCEDIRNAME}"/"${PROVIDERINSTANCEDIRNAME}"prov_templates.json | awk -F\" '{print $4}')

echo ''
echo -e "\033[1mShow ${PROVIDERINSTANCEDIRNAME}prov_templates.json 'podSpecYaml' file\033[0m"
sleep $SLEEP
echo "cat ${PODSPEC}"
cat "${PODSPEC}" || fail "Check install"

echo ''
echo -e "\033[1mConfirm the ${PROVIDERINSTANCEDIRNAME} provider instance directory structure\033[0m"
sleep $SLEEP
echo "tree \$HF_TOP/conf/providers/${PROVIDERINSTANCEDIRNAME}/"
tree "${HF_TOP}"/conf/providers/"${PROVIDERINSTANCEDIRNAME}"/ || fail "Check install"

echo ''
echo -e "\033[1mConfirm the provider instance is present and enabled\033[0m"
sleep $SLEEP
echo "grep -A2 -B1 ${PROVIDERINSTANCEDIRNAME} \$HF_TOP/conf/providers/hostProviders.json"
grep -A2 -B1 "${PROVIDERINSTANCEDIRNAME}" "${HF_TOP}"/conf/providers/hostProviders.json || fail "Check install"

echo ''
echo -e "\033[1mConfirm a requestor is configured to use the  provider instance\033[0m"
sleep $SLEEP
echo "grep ${PROVIDERINSTANCEDIRNAME} \$HF_TOP/conf/requestors/hostRequestors.json"
grep "${PROVIDERINSTANCEDIRNAME}" "${HF_TOP}"/conf/requestors/hostRequestors.json || fail "Check install"


## K8S_OPERATOR VALIDATION

echo ''
echo -e "\033[1mConfirm the provider operator manifest is applied\033[0m"
sleep $SLEEP
echo 'kubectl get pods --namespace gcp-symphony'
kubectl get pods --namespace gcp-symphony || fail "Check install"
