#!/usr/bin/env bash
# Purpose: Validate that the health and readiness endpoints of the operator are functioning correctly.
# Run from k8s-operator/tests/ci/kind-tests with an isolated Kubernetes context.

MAX_TIMEOUT_SECONDS=120 # 2 min
SERVER_HEALTHY=false
SERVER_READY=false
tmp_file="/tmp/tmp_check_$$.txt"

kubectl port-forward deployment.apps/$IMAGE 8080:8080 >/dev/null 2>&1 &
PF_PID=$!

sleep 20

cleanup() {
  echo "Cleaning up..."
  local exit_code=$?
  echo "Exit code: $exit_code"
  # Check if the port-forward PID is still running, then kill it
  if kill -0 "$PF_PID" 2>/dev/null; then
    kill "$PF_PID"
    wait "$PF_PID" 2>/dev/null
  fi
  # Clean up the temp file
  rm -f "$tmp_file" >/dev/null 2>&1
  exit $exit_code
}

trap cleanup EXIT INT TERM

START_TIME=$(date +%s)
while true; do
    curl -s http://localhost:8080/health > "$tmp_file" 2>/dev/null
    IS_HEALTHY=$?
    if [ $IS_HEALTHY -eq 0 ] && [ -s "$tmp_file" ]; then
        echo "Health server is responding with 200 OK."
        SERVER_HEALTHY=true
        break
    else
        echo "Health returned unexpected response: $IS_HEALTHY"
    fi

    if [[ $(($(date +%s) - $START_TIME)) -ge $MAX_TIMEOUT_SECONDS ]]; then
        echo "Failed: Timed out waiting for health server to be available."
        break
    fi

    sleep 5
done

START_TIME=$(date +%s)
while true; do
    curl -s http://localhost:8080/ready > "$tmp_file" 2>/dev/null
    IS_READY=$?
    if [ $IS_READY -eq 0 ] && [ -s "$tmp_file" ]; then
        echo "Readiness server is responding with 200 Ready."
        SERVER_READY=true
        break
    else
        echo "Readiness returned unexpected response: $IS_READY"
    fi

    if [[ $(($(date +%s) - $START_TIME)) -ge $MAX_TIMEOUT_SECONDS ]]; then
        echo "Failed: Timed out waiting for readiness server to be available."
        break
    fi

    sleep 5
done

if [ "$SERVER_HEALTHY" == "true" ] && [ "$SERVER_READY" == "true" ]; then
    echo "[PASS] Health and readiness servers are functioning correctly."
    exit 0
else
    echo "[FAIL] Health and/or readiness server did not respond as expected."
    exit 1
fi