#!/bin/bash

# AI Virtual Agent Installation Script with Environment Variable Collection
# This script consolidates all environment variable prompting and helm installation

set -e

# Parameters from Makefile
NAMESPACE="$1"
AI_VIRTUAL_AGENT_RELEASE="$2"
AI_VIRTUAL_AGENT_CHART="$3"

if [ -z "$NAMESPACE" ] || [ -z "$AI_VIRTUAL_AGENT_RELEASE" ] || [ -z "$AI_VIRTUAL_AGENT_CHART" ]; then
    echo "Usage: $0 <namespace> <release> <chart>"
    exit 1
fi

# Get script directory
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Source the environment variable collection script
source "$SCRIPT_DIR/collect_env_vars.sh"

# Build helm command arguments array to handle JSON properly
build_helm_cmd() {
    local cmd_args=()

    # Base command
    cmd_args+=("helm" "upgrade" "--install" "$AI_VIRTUAL_AGENT_RELEASE" "$AI_VIRTUAL_AGENT_CHART" "-n" "$NAMESPACE")

    # pgvector args
    cmd_args+=("--set" "pgvector.secret.user=$POSTGRES_USER")
    cmd_args+=("--set" "pgvector.secret.password=$POSTGRES_PASSWORD")
    cmd_args+=("--set" "pgvector.secret.dbname=$POSTGRES_DBNAME")

    # minio args
    cmd_args+=("--set" "minio.secret.user=$MINIO_USER")
    cmd_args+=("--set" "minio.secret.password=$MINIO_PASSWORD")

    # llm-service args
    cmd_args+=("--set" "llm-service.secret.hf_token=$HF_TOKEN")
    if [ -n "$LLM" ]; then
        cmd_args+=("--set" "global.models.$LLM.enabled=true")
    fi
    if [ -n "$SAFETY" ]; then
        cmd_args+=("--set" "global.models.$SAFETY.enabled=true")
    fi
    if [ -n "$LLM_TOLERATION" ]; then
        cmd_args+=("--set-json" "global.models.$LLM.tolerations=[{\"key\":\"$LLM_TOLERATION\",\"effect\":\"NoSchedule\",\"operator\":\"Exists\"}]")
    fi
    if [ -n "$SAFETY_TOLERATION" ]; then
        cmd_args+=("--set-json" "global.models.$SAFETY.tolerations=[{\"key\":\"$SAFETY_TOLERATION\",\"effect\":\"NoSchedule\",\"operator\":\"Exists\"}]")
    fi

    # llama-stack args (avoid duplicates with llm-service)
    if [ -n "$LLM_URL" ]; then
        cmd_args+=("--set" "global.models.$LLM.url=$LLM_URL")
    fi
    if [ -n "$SAFETY_URL" ]; then
        cmd_args+=("--set" "global.models.$SAFETY.url=$SAFETY_URL")
    fi
    if [ -n "$LLM_API_TOKEN" ]; then
        cmd_args+=("--set" "global.models.$LLM.apiToken=$LLM_API_TOKEN")
    fi
    if [ -n "$SAFETY_API_TOKEN" ]; then
        cmd_args+=("--set" "global.models.$SAFETY.apiToken=$SAFETY_API_TOKEN")
    fi
    if [ -n "$TAVILY_API_KEY" ]; then
        cmd_args+=("--set" "llama-stack.secrets.TAVILY_SEARCH_API_KEY=$TAVILY_API_KEY")
    fi
    if [ -n "$LLAMA_STACK_ENV" ]; then
        cmd_args+=("--set-json" "llama-stack.secrets=$LLAMA_STACK_ENV")
    fi

    # ingestion args
    cmd_args+=("--set" "configure-pipeline.notebook.create=false")
    cmd_args+=("--set" "ingestion-pipeline.defaultPipeline.enabled=false")
    cmd_args+=("--set" "ingestion-pipeline.authUser=${AUTH_INGESTION_PIPELINE_USER:-ingestion-pipeline}")

    # Oracle MCP server enablement (when ORACLE=true)
    if [[ "${ORACLE:-}" =~ ^(1|true|TRUE|yes|YES)$ ]]; then
        # Ensure Toolhive CRDs/operator are enabled and Oracle SQLcl MCP is enabled in subchart
        cmd_args+=("--set" "mcp-servers.toolhive.crds.enabled=true")
        cmd_args+=("--set" "mcp-servers.toolhive.operator.enabled=true")
        # Disable weather by default and enable oracle-sqlcl per new values structure
        cmd_args+=("--set" "mcp-servers.weather.enabled=false")
        cmd_args+=("--set" "mcp-servers.oracle-sqlcl.enabled=true")
    fi

    # seed admin user args
    if [ -n "$ADMIN_USERNAME" ]; then
        cmd_args+=("--set" "seed.admin_user.username=$ADMIN_USERNAME")
    fi
    if [ -n "$ADMIN_EMAIL" ]; then
        cmd_args+=("--set" "seed.admin_user.email=$ADMIN_EMAIL")
    fi

	# GCP args
	if [ -n "$GCP_SERVICE_ACCOUNT_FILE" ]; then
		cmd_args+=("--set-file" "llama-stack.gcpServiceAccountFile=$(realpath $GCP_SERVICE_ACCOUNT_FILE)")
	fi

	if [ -n "$VERTEX_AI_PROJECT" -a -n "$VERTEX_AI_LOCATION" ]; then
		cmd_args+=("--set" "llama-stack.vertexai.enabled=true")
		cmd_args+=("--set" "llama-stack.vertexai.projectId=$VERTEX_AI_PROJECT")
		cmd_args+=("--set" "llama-stack.vertexai.location=$VERTEX_AI_LOCATION")
	fi

    # extra helm args
    if [ -n "$EXTRA_HELM_ARGS" ]; then
        # Split EXTRA_HELM_ARGS and add each argument separately
        for arg in $EXTRA_HELM_ARGS; do
            cmd_args+=("$arg")
        done
    fi

    # Execute the command
    "${cmd_args[@]}"
}

echo "Installing $AI_VIRTUAL_AGENT_RELEASE helm chart in namespace $NAMESPACE"

# If ORACLE=true, pre-install Oracle 23ai database before the umbrella chart
# if [[ "${ORACLE:-}" =~ ^(1|true|TRUE|yes|YES)$ ]]; then
#     # Resolve Oracle chart path (override with ORACLE_CHART env var if provided)
#     DEFAULT_ORACLE_CHART_PATH="$SCRIPT_DIR/../../../../ai-architecture-charts/oracle23ai/helm"
#     ORACLE_CHART_PATH="${ORACLE_CHART:-$DEFAULT_ORACLE_CHART_PATH}"

#     if [ ! -d "$ORACLE_CHART_PATH" ]; then
#         echo "❌ Oracle chart not found at: $ORACLE_CHART_PATH"
#         echo "   Set ORACLE_CHART to the path of oracle23ai/helm or ensure the default path exists."
#         exit 1
#     fi

#     echo "📦 Installing/Upgrading Oracle 23ai (release: oracle23ai) from $ORACLE_CHART_PATH"
#     helm upgrade --install oracle23ai "$ORACLE_CHART_PATH" -n "$NAMESPACE"

#     # Mandatory readiness wait when ORACLE=true
#     ORACLE_WAIT_TIMEOUT_SECONDS=${ORACLE_WAIT_TIMEOUT_SECONDS:-1800}
#     echo "⏳ Waiting up to ${ORACLE_WAIT_TIMEOUT_SECONDS}s for Oracle StatefulSet to become ready..."
#     if command -v oc >/dev/null 2>&1; then
#         if ! oc rollout status statefulset/oracle23ai -n "$NAMESPACE" --timeout=${ORACLE_WAIT_TIMEOUT_SECONDS}s; then
#             echo "❌ Oracle StatefulSet did not become ready within timeout. Aborting."
#             exit 1
#         fi
#     else
#         if ! kubectl rollout status statefulset/oracle23ai -n "$NAMESPACE" --timeout=${ORACLE_WAIT_TIMEOUT_SECONDS}s; then
#             echo "❌ Oracle StatefulSet did not become ready within timeout. Aborting."
#             exit 1
#         fi
#     fi

#     echo "🔎 Verifying Oracle secret exists..."
#     ORACLE_SECRET_WAIT_SECONDS=${ORACLE_SECRET_WAIT_SECONDS:-600}
#     elapsed=0
#     interval=5
#     while [ $elapsed -lt $ORACLE_SECRET_WAIT_SECONDS ]; do
#         if kubectl get secret oracle23ai -n "$NAMESPACE" >/dev/null 2>&1; then
#             echo "✅ Oracle secret found"
#             break
#         fi
#         sleep $interval
#         elapsed=$((elapsed+interval))
#     done
#     if [ $elapsed -ge $ORACLE_SECRET_WAIT_SECONDS ]; then
#         echo "❌ Oracle secret not found after ${ORACLE_SECRET_WAIT_SECONDS}s. Aborting."
#         exit 1
#     fi
# fi

# Execute the helm command with proper argument handling
build_helm_cmd

echo "✅ Helm installation completed successfully!"
