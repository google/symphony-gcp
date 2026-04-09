#!/usr/bin/env bash
set -Eeuo pipefail
# =========================================
# Script Name: run-kind-tests.sh
# Description: Runs all shell test scripts in the adjacent kind-tests directory by
# invoking `bash` on each `*.sh` file; prints progress and fails fast on any error
# (script is executed with `set -Eeuo pipefail`).
# Author: Jheno Cerbito
# Date: 2026-04-10
# =========================================

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/kind-tests"

echo "[INFO] Running kind tests from directory: $TEST_DIR"

for test_script in "$TEST_DIR"/*.sh; do
    echo "[INFO] Running test script: $test_script"
    bash "$test_script"
done

echo
echo "[INFO] All kind tests passed successfully!"