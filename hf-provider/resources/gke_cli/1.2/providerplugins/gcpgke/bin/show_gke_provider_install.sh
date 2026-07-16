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

#Bash Variable
CHECK=$(printf '\u2713')
CROSS=$(printf '\u2717')


# Define Colors
RED='\e[31m'
NC='\e[0m' # No Color (Reset)
YELLOW='\e[33m'
BOLD='\e[1m'
BLNK='\e[5m'
RED_BOLD='\e[1;31m'
BG_RED='\e[41m'       # Red Background
FG_WHITE='\e[97;1m'   # Bold White Text
GREEN='\e[1;32m'
RED='\e[1;31m'
YELLOW='\e[1;33m'

# --- 2. Define the Spinner Function ---
# Usage: start_spinner "Message to display..."
start_spinner() {
    local message="$1"
    local frames="/-\|"

    echo -n "$message "

    # We run the actual while loop in the background
    while true; do
        for (( i=0; i<${#frames}; i++ )); do
            echo -en "\r$message [${frames:$i:1}]"
            sleep 0.1
        done
    done &

    # Save the Process ID of the background spinner loop
    SPINNER_PID=$!
}

# Usage: stop_spinner <0 for SUCCESS, 1 for FAILURE>
stop_spinner() {
    local status=$1

    # Kill the background spinner loop
    kill $SPINNER_PID 2>/dev/null
    wait $SPINNER_PID 2>/dev/null

    # Overwrite the line with the final result
    if [ "$status" -eq 0 ]; then
        echo -e "\r\033[K[${GREEN}PASSED${NC}]" # \033[K clears the rest of the line
    else
        echo -e "\r\033[K[${RED}FAILED${NC}]"
    fi
}

# =====================================================================
# --- 3. Your Actual Dependency Checks ---
# =====================================================================

echo "Starting System Dependency Checks..."
echo "------------------------------------"
echo " "
# --- Check 1: \$HF_TOP is present ---
start_spinner "Checking for \$HF_TOP..."
sleep 5

if [[ -n ${HF_TOP} ]]; then
    stop_spinner 0
          echo -e " ${GREEN}${CHECK}${NC} \$HF_TOP present"
else
    stop_spinner 1
          echo -e "   ${RED}${CROSS}${NC} ${YELLOW}-> \$HF_TOP is empty. Action required:${NC} Source your Symphony environment (e.g. '. \$EGO_TOP/profile.platform')"
exit 1
fi


echo " "
# --- Check 2: 'tree' command ---
start_spinner "Checking for 'tree' utility..."
sleep 5

if command -v tree > /dev/null 2>&1; then
    stop_spinner 0
    echo -e "  ${GREEN}${CHECK}${NC} 'tree' is installed."
    echo -e "tree utility is installed"
else
    stop_spinner 1
    echo -e "   ${RED}${CROSS}${NC} ${YELLOW}-> Tree package not installed:${NC} Run 'dnf install tree' to install."
fi

## Zero out the log file
# shellcheck disable=SC2188
> "${LOGFILE}"

## Show install info
# --- Check 3: Confirm the Symphony variables ---
echo " "
start_spinner "Checking for Symphony variables..."
sleep 5
if [[ -n "${HF_TOP}" && "${HF_VERSION}" ]]; then
stop_spinner 0
echo -e "  ${GREEN}${CHECK}${NC} Symphony variables are present"
echo -e "\$HF_TOP: ${YELLOW}${HF_TOP}${NC}"
echo -e "\$HF_VERSION: ${YELLOW}${HF_VERSION}${NC}"
else
stop_spinner 1
    echo -e "   ${RED}${CROSS}${NC} ${YELLOW}-> Symphony variables are missing"
fi


## HF_PROVIDER VALIDATION
# --- Check 4: Confirm the provider plugin directory structure ---
# Target directory path
TARGET_DIR="${HF_TOP}/${HF_VERSION}/providerplugins/${PROVIDERPLUGINSDIRNAME}"
echo ''
start_spinner "Checking for the provider plugin directory structure"
sleep 5

# Step 1: Check if the Directory Exists
if [ -d "$TARGET_DIR" ]; then
    # Directory exists! Stop the spinner as SUCCESS.
    stop_spinner 0
    echo -e "  ${GREEN}${CHECK}${NC} Directory structure confirmed."

    # Step 2: Check if the 'tree' command is installed

if command -v tree > /dev/null 2>&1; then
        echo -e "   Running: ${YELLOW}tree $TARGET_DIR${NC}"
        echo "------------------------------------"
        tree "$TARGET_DIR"
        echo "------------------------------------"
    else
        # Fallback if 'tree' is not installed
        echo -e "   ${YELLOW}[INFO]${NC} 'tree' package not installed. Falling back to 'ls'"
        echo "------------------------------------"
        ls -R "$TARGET_DIR"
        echo "------------------------------------"
    fi
else
    # Directory does not exist! Stop the spinner as FAILURE.
    stop_spinner 1
    echo -e "   ${RED}${CROSS}${NC} ${YELLOW}-> Error: Directory does not exist:${NC}"
    echo -e "      ${RED}$TARGET_DIR${NC}"
fi




# --- Check 5: Confirm the provider plugin is present and enabled ---
echo ''
start_spinner "Confirming the provider plugin is present and enabled..."
sleep 5
PROVPLUGIN_DIR="${HF_TOP}/conf/providerplugins"
PROVPLUGIN_FILE="${HF_TOP}/conf/providerplugins/hostProviderPlugins.json"

# Trap the output of the grep command so it doesn't break the spinner
if OUTPUT=$(grep -A1 -B1 "${PROVIDERPLUGINSDIRNAME}" "$PROVPLUGIN_FILE" 2>&1); then
    # Stop spinner as SUCCESS
    stop_spinner 0
    echo -e "  ${GREEN}${CHECK}${NC} Provider Plugin is present and enabled. Contents:"
    echo "------------------------------------"
    echo "$OUTPUT"
    echo "------------------------------------"

if command -v tree > /dev/null 2>&1; then
        echo -e "   Running: ${YELLOW}tree $PROVPLUGIN_DIR${NC}"
        echo "------------------------------------"
        tree "$PROVPLUGIN_DIR"
        echo "------------------------------------"
    else
        # Fallback if 'tree' is not installed
        echo -e "   ${YELLOW}[INFO]${NC} 'tree' package not installed. Falling back to 'ls'"
        echo "------------------------------------"
        ls -R "$PROVPLUGIN_DIR"
        echo "------------------------------------"
    fi



else
    # Stop spinner as FAILURE
    stop_spinner 1
    echo -e "   ${RED}${CROSS}${NC} ${YELLOW}-> Error: Provider plugin '${PROVIDERPLUGINSDIRNAME}' not found in:${NC}"
    echo -e "      ${RED}$PROVPLUGIN_FILE${NC}"
fi



# --- Check 6: Show the provider instance configuration directory and file ---
echo ''
start_spinner "Checking provider instance directory and config file..."
sleep 3

# Define absolute paths
PROV_INSTANCE_DIR="${HF_TOP}/conf/providers/${PROVIDERINSTANCEDIRNAME}"
PROV_CONFIG_FILE="${PROV_INSTANCE_DIR}/${PROVIDERINSTANCEDIRNAME}prov_config.json"

# Step 1: Validate that both the Directory and the specific JSON file exist
if [[ -d "$PROV_INSTANCE_DIR" && -f "$PROV_CONFIG_FILE" ]]; then

    # Step 2: Attempt to read the JSON file
    if CONFIG_OUTPUT=$(cat "$PROV_CONFIG_FILE" 2>&1); then
        # SUCCESS! Everything exists and is readable
        stop_spinner 0
        echo -e "  ${GREEN}${CHECK}${NC} Directory and configuration file confirmed."

        # Step 3: Display Directory Structure (Tree vs LS)
        if command -v tree > /dev/null 2>&1; then
            echo -e "   Running: ${YELLOW}tree $PROV_INSTANCE_DIR${NC}"
            echo "------------------------------------"
            tree "$PROV_INSTANCE_DIR"
            echo "------------------------------------"
        else
            echo -e "   ${YELLOW}[INFO]${NC} 'tree' package not installed. Falling back to 'ls':"
            echo "------------------------------------"
            ls -R "$PROV_INSTANCE_DIR"
            echo "------------------------------------"
        fi

        # Step 4: Display the JSON Configuration Content
        echo -e "   Contents of: ${YELLOW}${PROVIDERINSTANCEDIRNAME}prov_config.json${NC}"
        echo "------------------------------------"
        echo "$CONFIG_OUTPUT"
        echo "------------------------------------"

        # Step 5: Safely change directory for the remainder of the script
        cd "$PROV_INSTANCE_DIR"

    else
        # Failed to read the file (Permissions issue, etc.)
       stop_spinner 1
        echo -e "   ${RED}${CROSS}${NC} ${YELLOW}-> Error: Could not read configuration file:${NC}"
        echo -e "      ${RED}$PROV_CONFIG_FILE${NC}"
    fi

else
    # Directory or file is completely missing
    stop_spinner 1

    echo -e "   ${RED}${CROSS}${NC} ${YELLOW}-> Error: Missing provider instance directory or configuration file!${NC}"
    echo -e "      Expected Dir:  $PROV_INSTANCE_DIR"
    echo -e "      Expected File: $PROV_CONFIG_FILE"
fi




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
