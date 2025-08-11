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

    # seed admin user args
    if [ -n "$ADMIN_USERNAME" ]; then
        cmd_args+=("--set" "seed.admin_user.username=$ADMIN_USERNAME")
    fi
    if [ -n "$ADMIN_EMAIL" ]; then
        cmd_args+=("--set" "seed.admin_user.email=$ADMIN_EMAIL")
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

# Execute the helm command with proper argument handling
build_helm_cmd

echo "✅ Helm installation completed successfully!"
