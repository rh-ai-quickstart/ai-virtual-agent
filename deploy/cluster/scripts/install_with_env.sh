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

    # Model selection and Oracle MCP server enablement based on Oracle deployment
    if [[ "${ORACLE:-}" =~ ^(1|true|TRUE|yes|YES)$ ]]; then
        # Oracle deployment: Use 8B model with increased context length
        cmd_args+=("--set" "llm-service.models.llama-3-1-8b-instruct.enabled=true")
        cmd_args+=("--set" "llm-service.models.llama-3-2-1b-instruct.enabled=false")
        cmd_args+=("--set" "llm-service.models.llama-3-2-3b-instruct.enabled=false")
        # Add GPU toleration for G6E nodes
        cmd_args+=("--set-json" "llm-service.models.llama-3-1-8b-instruct.tolerations=[{\"key\":\"g6e-gpu\",\"effect\":\"NoSchedule\",\"operator\":\"Exists\"}]")
        echo "✅ Oracle deployment: Using 8B model with 131,072 token context length (default)"

        # Enable Oracle database installation
        cmd_args+=("--set" "mcp-servers.oracledb.enabled=true")
        # Ensure Toolhive CRDs/operator are enabled and Oracle SQLcl MCP is enabled in subchart
        cmd_args+=("--set" "mcp-servers.toolhive.crds.enabled=true")
        cmd_args+=("--set" "mcp-servers.toolhive.operator.enabled=true")
        # Enable oracle-sqlcl MCP server (most config is already in default values)
        cmd_args+=("--set" "mcp-servers.mcp-servers.oracle-sqlcl.enabled=true")
        cmd_args+=("--set" "mcp-servers.mcp-servers.oracle-sqlcl.image=quay.io/lrangine/sqlcl-mcp-server:4.0.3")
        # Enable 8B model in LlamaStack for Oracle deployment
        cmd_args+=("--set" "llama-stack.models.llama-3-1-8b-instruct.enabled=true")
        cmd_args+=("--set" "llama-stack.models.llama-3-1-8b-instruct.maxTokens=32768")
        cmd_args+=("--set" "llama-stack.models.llama-3-1-8b-instruct.url=http://llama-3-1-8b-instruct-predictor.\${env.NAMESPACE}.svc.cluster.local:8080/v1")
        cmd_args+=("--set" "llama-stack.models.llama-3-1-8b-instruct.apiToken=fake")
        # Disable 1B model in LlamaStack for Oracle deployment
        cmd_args+=("--set" "llama-stack.models.llama-3-2-1b-instruct.enabled=false")
        # Configure Oracle MCP server in LlamaStack
        cmd_args+=("--set" "llama-stack.mcp-servers.oracle_mcp_server.uri=http://mcp-oracle-sqlcl-proxy:8080/sse")
        echo "✅ Oracle MCP server configured in LlamaStack"
    else
        # Default deployment: Use 1B model for general use (most resource-efficient)
        cmd_args+=("--set" "llm-service.models.llama-3-2-1b-instruct.enabled=true")
        cmd_args+=("--set" "llm-service.models.llama-3-1-8b-instruct.enabled=false")
        cmd_args+=("--set" "llm-service.models.llama-3-2-3b-instruct.enabled=false")
        # Enable 1B model in LlamaStack for default deployment
        cmd_args+=("--set" "llama-stack.models.llama-3-2-1b-instruct.enabled=true")
        cmd_args+=("--set" "llama-stack.models.llama-3-2-1b-instruct.url=http://llama-3-2-1b-instruct-predictor.\${env.NAMESPACE}.svc.cluster.local:8080/v1")
        cmd_args+=("--set" "llama-stack.models.llama-3-2-1b-instruct.apiToken=fake")
        cmd_args+=("--set" "llama-stack.models.llama-3-1-8b-instruct.enabled=false")
        echo "✅ Default deployment: Using 1B model for general use (most resource-efficient)"
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

# Execute the helm command with proper argument handling
build_helm_cmd

echo "✅ Helm installation completed successfully!"
