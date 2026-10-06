#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
WORKSPACE_KEY="$(printf '%s' "$PROJECT_ROOT" | cksum | awk '{print $1}')"
STATE_DIR="${TMPDIR:-/tmp}/ai-virtual-agent-e2e-${UID:-$(id -u)}-${WORKSPACE_KEY}"
ENV_FILE="$STATE_DIR/test-env.sh"
PID_FILE="$STATE_DIR/port-forward-pids"

stop_forwards() {
    local failed=0
    local stopped=0
    if [[ -f "$PID_FILE" ]]; then
        local -a state=()
        mapfile -t state < "$PID_FILE"
        local index pid expected_service command_line process_state attempt
        for index in 0 2 4; do
            pid="${state[$index]:-}"
            expected_service="${state[$((index + 1))]:-}"
            if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
                command_line="$(ps -p "$pid" -o args= 2>/dev/null || true)"
                if [[ "$command_line" == *"port-forward"* \
                    && "$command_line" == *"--address 127.0.0.1"* ]]; then
                    kill -TERM "$pid" 2>/dev/null || true
                    for attempt in $(seq 1 50); do
                        process_state="$(ps -p "$pid" -o stat= 2>/dev/null || true)"
                        if [[ -z "$process_state" || "$process_state" == Z* ]]; then
                            break
                        fi
                        sleep 0.1
                    done
                    process_state="$(ps -p "$pid" -o stat= 2>/dev/null || true)"
                    if [[ -n "$process_state" && "$process_state" != Z* ]]; then
                        command_line="$(ps -p "$pid" -o args= 2>/dev/null || true)"
                        if [[ "$command_line" == *"port-forward"* \
                            && "$command_line" == *"--address 127.0.0.1"* ]]; then
                            kill -KILL "$pid" 2>/dev/null || true
                        fi
                        process_state="$(ps -p "$pid" -o stat= 2>/dev/null || true)"
                    fi
                    if [[ -n "$process_state" && "$process_state" != Z* ]]; then
                        echo "Could not stop OpenShift port-forward PID $pid for $expected_service." >&2
                        failed=1
                    else
                        echo "Stopped OpenShift port-forward PID $pid for $expected_service."
                        stopped=$((stopped + 1))
                    fi
                fi
            fi
        done
    fi
    if [[ "$failed" -ne 0 ]]; then
        echo "Port-forward state was kept at $PID_FILE so shutdown can be retried." >&2
        return 1
    fi
    rm -f "$PID_FILE" "$ENV_FILE"
    if [[ "$stopped" -eq 0 ]]; then
        echo "No active OpenShift E2E port-forwards were found."
    fi
}

wait_for_forward_url() {
    local label="$1"
    local namespace="$2"
    local service="$3"
    local local_port="$4"
    local remote_port="$5"
    local url="$6"
    local log_file="$7"
    local timeout="${8:-600}"
    local pid=""
    local deadline=$((SECONDS + timeout))
    local next_report=$((SECONDS + 30))

    : > "$log_file"
    while (( SECONDS < deadline )); do
        if [[ -z "$pid" ]] || ! kill -0 "$pid" 2>/dev/null; then
            nohup oc port-forward --address 127.0.0.1 -n "$namespace" \
                "$service" "$local_port:$remote_port" \
                >>"$log_file" 2>&1 </dev/null &
            pid=$!
            sleep 1
        fi
        if curl --fail --silent --show-error --max-time 2 "$url" >/dev/null 2>&1; then
            echo "$label is reachable at $url"
            FORWARD_PID="$pid"
            return 0
        fi
        if ! kill -0 "$pid" 2>/dev/null; then
            pid=""
        fi
        if (( SECONDS >= next_report )); then
            echo "Still waiting for $label at $url ($((deadline - SECONDS)) seconds remain)."
            next_report=$((SECONDS + 30))
        fi
        sleep 1
    done

    echo "$label did not become reachable at $url within $timeout seconds" >&2
    cat "$log_file" >&2
    [[ -n "$pid" ]] && kill "$pid" 2>/dev/null || true
    return 1
}

wait_for_job_complete() {
    local namespace="$1"
    local timeout="${E2E_DEFAULT_INGESTION_TIMEOUT:-1800s}"
    local job="$2"
    local description="$3"

    if ! oc get job "$job" -n "$namespace" >/dev/null 2>&1; then
        echo "Expected E2E $description job/$job was not found in namespace $namespace." >&2
        return 1
    fi

    echo "Waiting for $description job/$job to complete (timeout: $timeout)..."
    if oc wait --for=condition=complete "job/$job" \
        --timeout="$timeout" -n "$namespace"; then
        echo "$description job completed."
        return 0
    fi

    echo "$description job did not complete successfully." >&2
    oc describe job "$job" -n "$namespace" >&2 || true
    oc logs "job/$job" --all-containers=true --prefix -n "$namespace" >&2 || true
    return 1
}

wait_for_ingestion_status() {
    local namespace="$1"
    local service="$2"
    local base_url="$3"
    local pipeline_name="$4"
    local timeout="${E2E_INGESTION_STATUS_TIMEOUT_SECONDS:-1800}"
    local deadline=$((SECONDS + timeout))
    local status_json=""
    local state="unknown"

    echo "Waiting for fetch-and-store pipeline '$pipeline_name' to finish (timeout: ${timeout}s)..."
    while (( SECONDS < deadline )); do
        if status_json="$(curl --fail --silent --show-error --max-time 10 --get \
            --data-urlencode "pipeline_name=$pipeline_name" "$base_url/status" 2>&1)"; then
            state="$(printf '%s' "$status_json" | python3 -c \
                'import json, sys; print(json.load(sys.stdin).get("state", "unknown"))' \
                2>/dev/null || true)"
            case "${state,,}" in
                succeeded|success|complete|completed)
                    echo "Fetch-and-store pipeline '$pipeline_name' completed."
                    return 0
                    ;;
                failed|error)
                    echo "Fetch-and-store pipeline '$pipeline_name' failed: $status_json" >&2
                    oc logs -n "$namespace" "deployment/$service" \
                        --all-containers=true --prefix >&2 || true
                    return 1
                    ;;
            esac
        else
            state="waiting for status endpoint"
        fi
        sleep 5
    done

    echo "Fetch-and-store pipeline '$pipeline_name' did not finish within ${timeout}s; last state: $state" >&2
    echo "Last status response: $status_json" >&2
    oc logs -n "$namespace" "deployment/$service" \
        --all-containers=true --prefix >&2 || true
    return 1
}

start_forwards() {
    local namespace="$1"
    local release="$2"
    local backend_port="$3"
    local llamastack_port="$4"
    local app_service="$release"
    local backend_pid=""
    local llamastack_pid=""
    local ingestion_pid=""
    local service_start_timeout=600
    local ingestion_port="${E2E_INGESTION_PORT:-18001}"
    local ingestion_service="${release}-ingestion-pipeline"

    if [[ "$app_service" != *ai-virtual-agent* ]]; then
        app_service="${app_service}-ai-virtual-agent"
    fi
    if [[ ! "$backend_port" =~ ^[0-9]+$ || ! "$llamastack_port" =~ ^[0-9]+$ \
        || ! "$ingestion_port" =~ ^[0-9]+$ ]]; then
        echo "Port values must be numeric." >&2
        return 2
    fi
    if ! command -v oc >/dev/null 2>&1 || ! command -v curl >/dev/null 2>&1 \
        || ! command -v python3 >/dev/null 2>&1; then
        echo "oc, curl, and python3 are required to configure the OpenShift test environment." >&2
        return 2
    fi

    mkdir -p "$STATE_DIR"
    chmod 700 "$STATE_DIR"
    stop_forwards

    if ! wait_for_job_complete "$namespace" "upload-sample-docs-job" \
        "MinIO sample-document upload"; then
        return 1
    fi
    if ! wait_for_job_complete "$namespace" "add-default-ingestion-pipeline" \
        "default ingestion pipeline registration"; then
        return 1
    fi

    if ! wait_for_forward_url "LlamaStack" "$namespace" svc/llamastack \
        "$llamastack_port" 8321 "http://127.0.0.1:$llamastack_port/v1/health" \
        "$STATE_DIR/llamastack.log" "$service_start_timeout"; then
        return 1
    fi
    llamastack_pid="$FORWARD_PID"

    if ! wait_for_forward_url "Backend" "$namespace" "svc/$app_service" \
        "$backend_port" 8000 "http://127.0.0.1:$backend_port/api/v1/openapi.json" \
        "$STATE_DIR/backend.log" "$service_start_timeout"; then
        kill "$llamastack_pid" 2>/dev/null || true
        return 1
    fi
    backend_pid="$FORWARD_PID"

    local model_deadline=$((SECONDS + service_start_timeout))
    local next_model_report=$((SECONDS + 30))
    local models_ready=false
    while (( SECONDS < model_deadline )); do
        if curl --fail --silent --max-time 10 \
            "http://127.0.0.1:$backend_port/api/v1/llama_stack/llms" \
            2>/dev/null \
            | python3 -c 'import json, sys; models = json.load(sys.stdin); sys.exit(0 if isinstance(models, list) and models else 1)' \
                >/dev/null 2>&1; then
            echo "At least one inference model is available."
            models_ready=true
            break
        fi
        if (( SECONDS >= next_model_report )); then
            echo "Waiting for LlamaStack to report an inference model. Check LLM_URL, LLM_ID, and LLM_API_TOKEN if this continues."
            next_model_report=$((SECONDS + 30))
        fi
        sleep 5
    done
    if [[ "$models_ready" != true ]]; then
        echo "LlamaStack did not report any inference models within $service_start_timeout seconds." >&2
        echo "Check the LlamaStack pod logs and the LLM_URL, LLM_ID, and LLM_API_TOKEN values." >&2
        cat "$STATE_DIR/llamastack.log" >&2
        kill "$backend_pid" "$llamastack_pid" 2>/dev/null || true
        return 1
    fi

    if ! wait_for_forward_url "Ingestion pipeline" "$namespace" \
        "svc/$ingestion_service" "$ingestion_port" 80 \
        "http://127.0.0.1:$ingestion_port/ping" \
        "$STATE_DIR/ingestion-pipeline.log" "$service_start_timeout"; then
        kill "$backend_pid" "$llamastack_pid" 2>/dev/null || true
        return 1
    fi
    ingestion_pid="$FORWARD_PID"

    if ! wait_for_ingestion_status "$namespace" "$ingestion_service" \
        "http://127.0.0.1:$ingestion_port" "zippity-zoo-vector-db"; then
        kill "$backend_pid" "$llamastack_pid" "$ingestion_pid" 2>/dev/null || true
        return 1
    fi

    umask 077
    printf '%s\n' "$backend_pid" "svc/$app_service" \
        "$llamastack_pid" "svc/llamastack" \
        "$ingestion_pid" "svc/$ingestion_service" > "$PID_FILE"
    {
        printf 'export TEST_BACKEND_URL="http://127.0.0.1:%s"\n' "$backend_port"
        printf 'export TEST_FRONTEND_URL="http://127.0.0.1:%s"\n' "$backend_port"
        printf 'export TEST_LLAMASTACK_URL="http://127.0.0.1:%s"\n' "$llamastack_port"
        printf 'export TEST_INGESTION_PIPELINE_URL="http://127.0.0.1:%s"\n' "$ingestion_port"
        printf 'export TEST_E2E_DEPLOYMENT="true"\n'
    } > "$ENV_FILE"
    echo "OpenShift E2E port-forwards are running for namespace $namespace."
}

run_tests() {
    if [[ ! -f "$ENV_FILE" ]]; then
        exec make -C "$PROJECT_ROOT/deploy/local" test-int
    fi
    if ! python3 -c 'import pytest, requests, tavern, xdist' >/dev/null 2>&1; then
        echo "Install the integration test dependencies with:" >&2
        echo "  python3 -m pip install -r tests/requirements.txt" >&2
        return 2
    fi
    # The file is generated by this script and contains only loopback service URLs.
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    cd "$PROJECT_ROOT"
    ./tests/run_tests.sh --integration
}

case "${1:-}" in
    start)
        if [[ $# -ne 5 ]]; then
            echo "Usage: $0 start <namespace> <release> <backend-port> <llamastack-port>" >&2
            exit 2
        fi
        start_forwards "$2" "$3" "$4" "$5"
        ;;
    test)
        run_tests
        ;;
    stop)
        stop_forwards
        echo "OpenShift E2E port-forward shutdown complete."
        ;;
    *)
        echo "Usage: $0 {start|test|stop} [arguments]" >&2
        exit 2
        ;;
esac
