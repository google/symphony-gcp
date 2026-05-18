#!/usr/bin/env bash

# =========================================
# Script Name: run-kind-tests.sh
# Description: Runs all shell test scripts in the adjacent kind-tests directory by
# invoking `bash` on each `*.sh` file; prints progress and fails fast on any error
# (script is executed with `set -Eeuo pipefail`).
# Author: Jheno Cerbito
# Date: 2026-04-10
# =========================================

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/kind-tests"
LOG_FILE="integration-test.log" 
: > "$LOG_FILE" # Clear log file at the start
MAX_PARALLEL=2
# Define color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# initialize variables
passed=0
failed=0
running=0
failed_tests=()
jobs=()

echo "[INFO] Waiting for CRDs to be established..."

kubectl wait --for=condition=Established \
    crd/gcp-symphony-resources.accenture.com \
    --timeout=60s
    
kubectl wait --for=condition=Established \
    crd/machine-return-requests.accenture.com \
    --timeout=60s

echo "[INFO] Running integration test from directory: $TEST_DIR" | tee -a "$LOG_FILE"

run_test() {
    local test="$1"
    set -o pipefail
    echo "[$(date +'%Y-%m-%d %H:%M:%S')][INFO][$(basename "$test")] - Running test..." | tee -a "$LOG_FILE"
    bash "$test" 2>&1 | while IFS= read -r line; do
        echo "[$(date +'%Y-%m-%d %H:%M:%S')][INFO][$(basename "$test")] - $line"
    done | tee -a "$LOG_FILE"

    return ${PIPESTATUS[0]}
}

handle_finished_job() {
    wait -n 
    for pi in "${!jobs[@]}"; do
        if ! kill -0 "$pi" 2>/dev/null; then
            wait "$pi"
            status=$?
            test_name="${jobs[$pi]}"
            if [ "$status" -eq 0 ]; then
                echo -e "${GREEN}[PASSED] $test_name${NC}"
                ((passed+=1))
            else
                echo -e "${RED}[FAILED] $test_name${NC}"
                ((failed+=1))
                failed_tests+=("$test_name")
            fi
            unset "jobs[$pi]"
            ((running-=1))
            break
        fi
    done
}

for t in "$TEST_DIR"/*.sh; do
    run_test "$t" &
    pid=$!

    jobs[$pid]="$(basename "$t")"

    ((running+=1))

    if [ "$running" -ge "$MAX_PARALLEL" ]; then
        handle_finished_job
    fi
done

while [ "$running" -gt 0 ]; do
    handle_finished_job
done

if [ "$failed" -gt 0 ]; then
    echo ""
    echo "=============================================" 
    echo " "

        echo -e "${RED}Failed test cases:${NC}" 
        for ft in "${failed_tests[@]}"; do
            echo -e "${RED} - $ft${NC}" 
        done

    echo " "
    echo "============================================="
fi
echo "======== $passed passed, $failed failed, $((passed + failed)) total ========" | tee -a "$LOG_FILE"
if [[ $failed -gt 0 ]]; then
    echo -e "${RED}[ERROR] Some tests failed. Please check the log file '$LOG_FILE' for details.${NC}"
    exit 1
else
    echo -e "${GREEN}[INFO] All integration tests passed successfully!${NC}"
    exit 0
fi