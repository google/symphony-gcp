#!/bin/bash
SLEEP=1
PROVIDERPLUGINSDIRNAME=gcpgce
PROVIDERINSTANCEDIRNAME=gcpgceinst
LOGFILE=/dev/null

function fail() {
  echo -e "\e[0;31mError: $1\e[0m" >&2 # Send message to stderr
#  exit "${2:-1}" # Return a code specified by $2, or 1 by default
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
            usage >&2
            ;;
        \?) # Handle invalid options
            printf "*** Invalid option: -%s\n" "$OPTARG" >&2
            usage >&2
            ;;
    esac
done

# Shift processed arguments so the main script can use remaining positional arguments
shift $((OPTIND - 1))

## Redirect stdout to a process substitution that runs tee
## Remove ANSI color sequences, Cursor movement codes & Spinner carriage returns
exec > >(
    tee >(
        sed -E '
            s/\x1B\[[0-9;]*[A-Za-z]//g;
            s/\r[^\n]*//g;
        ' > "$LOGFILE"
    )
)

## Redirect stderr to the same place as stdout
exec 2>&1


#Bash Variable
CHECK=$(printf '\u2713')
CROSS=$(printf '\u2717')

# Define Colors
NC='\e[0m' # No Color (Reset)
GREEN='\e[1;32m'
RED='\e[1;31m' #Red Bold
YELLOW='\e[1;33m' #Yellow Bold

# --- 1. Define the Spinner Function ---
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
echo ''
echo "Starting System Dependency Checks..."
echo "------------------------------------"
echo ''
# --- Check 1: \$HF_TOP is present ---
start_spinner "Checking for \$HF_TOP..."
sleep $SLEEP

if [[ -n ${HF_TOP} ]]; then
    stop_spinner 0
          echo -e " ${GREEN}${CHECK}${NC} \$HF_TOP present"
else
    stop_spinner 1
          echo -e "   ${RED}${CROSS}${NC} ${YELLOW}-> \$HF_TOP is empty. Action required:${NC} Source your Symphony environment (e.g. '. \$EGO_TOP/profile.platform')"
exit 1
fi


echo ''
# --- Check 2: 'tree' command ---
start_spinner "Checking for 'tree' utility..."
sleep $SLEEP

if command -v tree > /dev/null 2>&1; then
    stop_spinner 0
    echo -e "  ${GREEN}${CHECK}${NC} 'tree' package is installed."

else
    stop_spinner 1
    echo -e "   ${RED}${CROSS}${NC} ${YELLOW}-> Tree package not installed:${NC} Run 'dnf install tree' to install."

fi


## Zero out the log file
# shellcheck disable=SC2188
> "${LOGFILE}"

## Show install info
# --- Check 3: Confirm the Symphony variables ---
echo ''
echo -e "\033[1mConfirm the Symphony variables\033[0m"
start_spinner "Checking for Symphony variables..."
sleep $SLEEP

if [[ -n "${HF_TOP}" && "${HF_VERSION}" ]]; then
   stop_spinner 0
   echo -e "  ${GREEN}${CHECK}${NC} Symphony variables are present"
   echo -e "\$HF_TOP: ${YELLOW}${HF_TOP}${NC}"
   echo -e "\$HF_VERSION: ${YELLOW}${HF_VERSION}${NC}"

else
   stop_spinner 1
   echo -e "   ${RED}${CROSS}${NC} ${YELLOW}-> \$HF_TOP is empty. ${NC}Source your Symphony environment (e.g. '. \$EGO_TOP/profile.platform')"

fi


## HF_PROVIDER VALIDATION
# --- Check 4: Confirm the provider plugin directory structure ---
# Target directory path
TARGET_DIR="${HF_TOP}/${HF_VERSION}/providerplugins/${PROVIDERPLUGINSDIRNAME}"
echo ''
echo -e "\033[1mConfirm the provider plugin directory structure\033[0m"

# Step 1: Check if the Directory Exists
if [ -d "$TARGET_DIR" ]; then

  # Step 2: Check if the 'tree' command is installed
  if command -v tree > /dev/null 2>&1; then
        echo "---------------------"
        echo -e "${YELLOW}Executing command:${NC}"
        echo "   tree $TARGET_DIR"
        echo "---------------------"
        start_spinner "Checking for the provider plugin directory structure"
        sleep $SLEEP
        stop_spinner 0
        echo -e "  ${GREEN}${CHECK}${NC} Directory structure confirmed. Result:"
        echo "------------------------------------"
        tree "$TARGET_DIR"
        echo "------------------------------------"

    else
        # Fallback if 'tree' is not installed
        echo -e "   ${YELLOW}[INFO]${NC} 'tree' package not installed. Falling back to 'ls'"
        echo "---------------------"
        echo -e "${YELLOW}Executing command:${NC}"
        echo "  ls -R $TARGET_DIR"
        echo "---------------------"
        start_spinner "Checking for the provider plugin directory structure"
        sleep $SLEEP
        stop_spinner 0
        echo -e "  ${GREEN}${CHECK}${NC} Directory structure confirmed. Result:"
        echo "------------------------------------"
        ls -R "$TARGET_DIR"
    
    fi

else
    # Directory does not exist!.
  if command -v tree > /dev/null 2>&1; then
        echo "---------------------"
        echo -e "${YELLOW}Executing command:${NC}"
        echo "   tree $TARGET_DIR"
        echo "---------------------"
        start_spinner "Checking for the provider plugin directory structure"
        sleep $SLEEP
        stop_spinner 1
        echo -e "   ${RED}${CROSS}${NC} ${YELLOW}-> Error: Directory '${PROVIDERPLUGINSDIRNAME}' does not exist:${NC}"
        tree "$TARGET_DIR"
        echo "------------------------------------"

    else
        # Fallback if 'tree' is not installed
        echo -e "   ${YELLOW}[INFO]${NC} 'tree' package not installed. Falling back to 'ls'"
        echo "---------------------"
        echo -e "${YELLOW}Executing command:${NC}"
        echo "  ls -R $TARGET_DIR"
        echo "---------------------"
        start_spinner "Checking for the provider plugin directory structure"
        sleep $SLEEP
        stop_spinner 1
        echo -e "   ${RED}${CROSS}${NC} ${YELLOW}-> Error: Directory '${PROVIDERPLUGINSDIRNAME}' does not exist:${NC}"
        ls -R "$TARGET_DIR"
    
    fi

fi


# --- Check 5: Confirm the provider plugin is present and enabled ---
echo ''
echo -e "\033[1mConfirm the provider plugin is present and enabled\033[0m"
PROVPLUGIN_FILE="${HF_TOP}/conf/providerplugins/hostProviderPlugins.json"

if OUTPUT=$(grep -A1 -B1 "${PROVIDERPLUGINSDIRNAME}" "$PROVPLUGIN_FILE" 2>&1); then
    echo "---------------------"
    echo -e "${YELLOW}Executing command:${NC}"
    echo "     grep -A1 -B1 "${PROVIDERPLUGINSDIRNAME}" \$HF_TOP/conf/providerplugins/hostProviderPlugins.json"
    echo "---------------------"
    start_spinner "Checking the provider plugin is present and enabled..."
    sleep $SLEEP
    stop_spinner 0
    echo -e "  ${GREEN}${CHECK}${NC} Provider Plugin is present and enabled. Result:"
    echo "------------------------------------"
    echo "$OUTPUT"

else
    echo "---------------------"
    echo -e "${YELLOW}Executing command:${NC}"
    echo "  grep -A1 -B1 "${PROVIDERPLUGINSDIRNAME}" \$HF_TOP/conf/providerplugins/hostProviderPlugins.json"
    echo "---------------------"
    start_spinner "Checking the provider plugin is present and enabled..."
    sleep $SLEEP
    stop_spinner 1
    echo -e "   ${RED}${CROSS}${NC} ${YELLOW}-> Error: Provider plugin '${PROVIDERPLUGINSDIRNAME}' not found.${NC}"
    grep -A1 -B1 "${PROVIDERPLUGINSDIRNAME}" "$PROVPLUGIN_FILE"

fi


# --- Check 6: Change to the provider instance directory ---
echo ''
echo -e "\033[1mChange to the provider instance directory\033[0m"

PROVIDER_DIR="${HF_TOP}/conf/providers/${PROVIDERINSTANCEDIRNAME}"

if cd "$PROVIDER_DIR" > /dev/null 2>&1; then
    echo "---------------------"
    echo -e "${YELLOW}Executing command:${NC}"
    echo "   cd \$HF_TOP/conf/providers/${PROVIDERINSTANCEDIRNAME}/"
    echo "---------------------"
    start_spinner "Changing to the provider instance directory..."
    sleep $SLEEP
    stop_spinner 0
    echo -e "  ${GREEN}${CHECK}${NC} Changed to provider instance directory."

else
    echo "---------------------"
    echo -e "${YELLOW}Executing command:${NC}"
    echo "   cd \$HF_TOP/conf/providers/${PROVIDERINSTANCEDIRNAME}/"
    echo "---------------------"
    stop_spinner 1
    echo -e "   ${RED}${CROSS}${NC} ${YELLOW}-> Error: Could not change to directory:${NC}"
    cd "$PROVIDER_DIR"

fi


# --- Check 7: Show the provider instance ${PROVIDERINSTANCEDIRNAME}prov_config.json file ---
echo ''
echo -e "\033[1mShow the provider instance ${PROVIDERINSTANCEDIRNAME}prov_config.json file\033[0m"

# Define absolute paths
PROV_CONFIG_FILE="$HF_TOP/conf/providers/${PROVIDERINSTANCEDIRNAME}/${PROVIDERINSTANCEDIRNAME}prov_config.json"

# Step 1: Attempt to read the ${PROVIDERINSTANCEDIRNAME}prov_config.json file
if CONFIG_OUTPUT=$(cat ${PROV_CONFIG_FILE} 2>&1); then
    echo "---------------------"
    echo -e "${YELLOW}Executing command:${NC}"
    echo " cat \$HF_TOP/conf/providers/${PROVIDERINSTANCEDIRNAME}/${PROVIDERINSTANCEDIRNAME}prov_config.json"
    echo "---------------------"
    start_spinner "Checking the provider instance ${PROVIDERINSTANCEDIRNAME}prov_config.json file..."
    stop_spinner 0
    echo -e "  ${GREEN}${CHECK}${NC} Provider instance configured. Result:"
    echo "------------------------------------"
    cat ${PROVIDERINSTANCEDIRNAME}prov_config.json

else
    echo "---------------------"
    echo -e "${YELLOW}Executing command:${NC}"
    echo " cat \$HF_TOP/conf/providers/${PROVIDERINSTANCEDIRNAME}/${PROVIDERINSTANCEDIRNAME}prov_config.json"
    echo "---------------------"
    stop_spinner 1
    echo -e "   ${RED}${CROSS}${NC} ${YELLOW}-> Error: Provider instance config file is missing.${NC}"
    echo "$CONFIG_OUTPUT"

fi


# --- Check 8: Show the provider instance ${PROVIDERINSTANCEDIRNAME}prov_templates.json file
echo ''
echo -e "\033[1mShow the provider instance ${PROVIDERINSTANCEDIRNAME}prov_templates.json file\033[0m"

TEMPLATE_FILE="${HF_TOP}/conf/providers/${PROVIDERINSTANCEDIRNAME}/${PROVIDERINSTANCEDIRNAME}prov_templates.json"

if OUTPUT=$(cat "$TEMPLATE_FILE" 2>&1); then
    echo "---------------------"
    echo -e "${YELLOW}Executing command:${NC}"
    echo "   cat \$HF_TOP/conf/providers/${PROVIDERINSTANCEDIRNAME}/${PROVIDERINSTANCEDIRNAME}prov_templates.json"
    echo "---------------------"
    start_spinner "Show the provider instance ${PROVIDERINSTANCEDIRNAME}prov_templates.json file..."
    sleep $SLEEP
    stop_spinner 0
    echo -e "  ${GREEN}${CHECK}${NC}Template file found. Result:"
    echo "------------------------------------"
    echo "$OUTPUT"

else
    echo "---------------------"
    echo -e "${YELLOW}Executing command:${NC}"
    echo "   cat \$HF_TOP/conf/providers/${PROVIDERINSTANCEDIRNAME}/${PROVIDERINSTANCEDIRNAME}prov_templates.json"
    echo "---------------------"
    start_spinner "Show the provider instance ${PROVIDERINSTANCEDIRNAME}prov_templates.json file..."
    sleep $SLEEP
    stop_spinner 1
    echo -e "   ${RED}${CROSS}${NC} ${YELLOW}-> Error: Template file missing.${NC}"
    echo "$OUTPUT"

fi


# --- Check 9: Confirm the ${PROVIDERINSTANCEDIRNAME} provider instance directory structure ---
echo ''
echo -e "\033[1mConfirm the ${PROVIDERINSTANCEDIRNAME} provider instance directory structure\033[0m"

# Define absolute paths
PROV_INSTANCE_DIR="${HF_TOP}/conf/providers/${PROVIDERINSTANCEDIRNAME}"

# Step 1: Validate that the gcpgceinstprov_config.json file exist
if [ -d "$PROV_INSTANCE_DIR" ]; then

        # Step 2: Display Directory Structure (Tree vs LS)
        if command -v tree > /dev/null 2>&1; then
            echo "---------------------"
            echo -e "${YELLOW}Executing command:${NC}"
            echo "   tree $PROV_INSTANCE_DIR"
            echo "---------------------"
            start_spinner "Checking the ${PROVIDERINSTANCEDIRNAME} provider instance directory structure..."
            sleep $SLEEP
            stop_spinner 0
            echo -e "  ${GREEN}${CHECK}${NC} Provider instance directory structure confirmed. Result:"
            echo "------------------------------------"
            tree "$PROV_INSTANCE_DIR"
            echo "------------------------------------"
        else
            echo -e "   ${YELLOW}[INFO]${NC} 'tree' package not installed. Falling back to 'ls':"
            echo "---------------------"
            echo -e "${YELLOW}Executing command:${NC}"
            echo "   tree $PROV_INSTANCE_DIR"
            echo "---------------------"
            start_spinner "Checking the ${PROVIDERINSTANCEDIRNAME} provider instance directory structure..."
            sleep $SLEEP
            stop_spinner 0
            echo -e "  ${GREEN}${CHECK}${NC} Provider instance directory structure confirmed. Result:"
            echo "------------------------------------"
            ls -R "$PROV_INSTANCE_DIR"
        
        fi

else
    # Directory is missing
    if command -v tree > /dev/null 2>&1; then
        echo "---------------------"
        echo -e "${YELLOW}Executing command:${NC}"
        echo "   tree $PROV_INSTANCE_DIR"
        echo "---------------------"
        start_spinner "Checking the ${PROVIDERINSTANCEDIRNAME} provider instance directory structure..."
        sleep $SLEEP
        stop_spinner 1
        echo -e "   ${RED}${CROSS}${NC} ${YELLOW}-> Error: Missing provider instance directory.${NC}"
        tree "$PROV_INSTANCE_DIR"
        echo "------------------------------------"
     else
        echo -e "   ${YELLOW}[INFO]${NC} 'tree' package not installed. Falling back to 'ls':"
        echo "---------------------"
        echo -e "${YELLOW}Executing command:${NC}"
        echo "   tree $PROV_INSTANCE_DIR"
        echo "---------------------"
        start_spinner "Checking the ${PROVIDERINSTANCEDIRNAME} provider instance directory structure..."
        sleep $SLEEP
        stop_spinner 1
        echo -e "   ${RED}${CROSS}${NC} ${YELLOW}-> Error: Missing provider instance directory.${NC}"
        ls -R "$PROV_INSTANCE_DIR"
     
     fi

fi


# --- Check 10: Confirm the provider instance is present and enabled
echo ''
echo -e "\033[1mConfirm the provider instance is present and enabled\033[0m"

HOST_PROVIDERS="${HF_TOP}/conf/providers/hostProviders.json"

if PROV_INST_OUTPUT=$(grep -A2 -B1 "${PROVIDERINSTANCEDIRNAME}" "$HOST_PROVIDERS" 2>&1); then
    echo "---------------------"
    echo -e "${YELLOW}Executing command:${NC}"
    echo "   grep -A2 -B1 "${PROVIDERINSTANCEDIRNAME}" \$HF_TOP/conf/providers/hostProviders.json"
    echo "---------------------"
    start_spinner "Checking if provider instance is present and enabled..."
    sleep $SLEEP
    stop_spinner 0
    echo -e "  ${GREEN}${CHECK}${NC} Provider instance is enabled. Result:"
    echo "------------------------------------"
    echo "$PROV_INST_OUTPUT"

else
    echo "---------------------"
    echo -e "${YELLOW}Executing command:${NC}"
    echo "   grep -A2 -B1 "${PROVIDERINSTANCEDIRNAME}" \$HF_TOP/conf/providers/hostProviders.json"
    echo "---------------------"
    start_spinner "Checking if provider instance is present and enabled..."
    sleep $SLEEP
    stop_spinner 1
    echo -e "   ${RED}${CROSS}${NC} ${YELLOW}-> Error: Provider instance '${PROVIDERINSTANCEDIRNAME}' not found.${NC}"
    echo "$PROV_INST_OUTPUT"

fi


# --- Check 11: Confirm a requestor is configured to use the  provider instance
echo ''
echo -e "\033[1mConfirm a requestor is configured to use the  provider instance\033[0m"

HOST_REQUESTORS="${HF_TOP}/conf/requestors/hostRequestors.json"

if REQ_OUTPUT=$(grep "${PROVIDERINSTANCEDIRNAME}" "$HOST_REQUESTORS" 2>&1); then
    echo "---------------------"
    echo -e "${YELLOW}Executing command:${NC}"
    echo "   grep "${PROVIDERINSTANCEDIRNAME}" \$HF_TOP/conf/requestors/hostRequestors.json"
    echo "---------------------"
    start_spinner "Checking if a requestor is configured to use the  provider instance..."
    sleep $SLEEP
    stop_spinner 0
    echo -e "  ${GREEN}${CHECK}${NC} Provider instance '${PROVIDERINSTANCEDIRNAME}' found in the requestor. Result:${NC}"
    echo "------------------------------------"
    grep -E "name|provider" "$HOST_REQUESTORS"

else
    echo "---------------------"
    echo -e "${YELLOW}Executing command:${NC}"
    echo "   grep "${PROVIDERINSTANCEDIRNAME}" \$HF_TOP/conf/requestors/hostRequestors.json"
    echo "---------------------"
    start_spinner "Checking if a requestor is configured to use the  provider instance..."
    sleep $SLEEP
    stop_spinner 1
    echo -e "   ${RED}${CROSS}${NC} ${YELLOW}-> Error: Provider instance '${PROVIDERINSTANCEDIRNAME}' not found in the requestor.${NC}"
    grep -E "name|provider" "$HOST_REQUESTORS"

fi
