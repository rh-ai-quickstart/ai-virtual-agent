#!/bin/bash

# AI Virtual Agent Environment Variable Collection Script
# This script collects all necessary environment variables for deployment
# and outputs them in a format that can be sourced by the Makefile

set -e

# Function to prompt for a value with optional default
prompt_for_value() {
    local var_name="$1"
    local prompt_text="$2"
    local default_value="$3"
    local current_value="${!var_name}"

    # If the variable is already set (from environment), use it
    if [ -n "$current_value" ]; then
        echo "$current_value"
        return
    fi

    # Otherwise prompt for it
    if [ -n "$default_value" ]; then
        read -r -p "$prompt_text [$default_value]: " input_value
        echo "${input_value:-$default_value}"
    else
        read -r -p "$prompt_text: " input_value
        echo "$input_value"
    fi
}

# Function to prompt for optional value with informational text
prompt_for_optional_value() {
    local var_name="$1"
    local prompt_text="$2"
    local info_text="$3"
    local current_value="${!var_name}"

    # If the variable is already set (from environment), use it
    if [ -n "$current_value" ]; then
        echo "$current_value"
        return
    fi

    # Show informational text if provided
    if [ -n "$info_text" ]; then
        echo ""
        echo "$info_text"
        echo ""
    fi

    read -r -p "$prompt_text: " input_value
    echo "$input_value"
}

# Collect all required environment variables
echo "🔧 Collecting environment variables for AI Virtual Agent deployment..."
echo ""

# Hugging Face Token (required)
HF_TOKEN=$(prompt_for_value "HF_TOKEN" "Enter Hugging Face Token")

# Tavily API Key (optional but recommended) - always show info
echo ""
echo "💡 Tavily Search API Key"
echo "     Without a key, web search capabilities will be disabled in your AI agents."
echo "     To enable web search, obtain a key from https://tavily.com/"
echo ""
TAVILY_API_KEY=$(prompt_for_value "TAVILY_API_KEY" "Enter Tavily API Key now (or press Enter to continue without web search)" "")

# SerpApi API Key (optional, enables hotel and flight search in vacation planner)
echo ""
echo "💡 SerpApi API Key"
echo "     Without a key, hotel and flight search will be disabled in vacation planner agents."
echo "     To enable, obtain a key from https://serpapi.com/"
echo ""
SERPAPI_API_KEY=$(prompt_for_value "SERPAPI_API_KEY" "Enter SerpApi API Key now (or press Enter to skip)" "")

# MaaS (Model as a Service) configuration for LangGraph / CrewAI runners
echo ""
echo "💡 MaaS Configuration (optional)"
echo "     Set these to point LangGraph and CrewAI runners at an external model endpoint"
echo "     instead of the local LlamaStack inference. Leave blank to use LlamaStack."
echo ""
MAAS_API_BASE=$(prompt_for_value "MAAS_API_BASE" "Enter MaaS API base URL (or press Enter to skip)" "")
if [ -n "$MAAS_API_BASE" ]; then
    MAAS_API_KEY=$(prompt_for_value "MAAS_API_KEY" "Enter MaaS API key" "")
    MAAS_MODEL_NAME=$(prompt_for_value "MAAS_MODEL_NAME" "Enter MaaS model name" "")
fi

# Keycloak admin password
KC_ADMIN_PASS=$(prompt_for_value "KC_ADMIN_PASS" "Enter Keycloak admin password" "changemeplease")

# App admin user (for ai-apps realm)
echo ""
echo "💡 Application Admin User"
echo "     This creates an admin user in the ai-apps realm so you can log into"
echo "     the application immediately after install."
echo ""
APP_ADMIN_USERNAME=$(prompt_for_value "APP_ADMIN_USERNAME" "Enter app admin username" "admin")
APP_ADMIN_PASSWORD=$(prompt_for_value "APP_ADMIN_PASSWORD" "Enter app admin password" "changeme")
APP_ADMIN_EMAIL=$(prompt_for_value "APP_ADMIN_EMAIL" "Enter app admin email")
while [ -z "$APP_ADMIN_EMAIL" ]; do
    echo "  Email is required."
    APP_ADMIN_EMAIL=$(prompt_for_value "APP_ADMIN_EMAIL" "Enter app admin email")
done

# Database configuration (use defaults, don't prompt)
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-rag_password}"
POSTGRES_DBNAME="${POSTGRES_DBNAME:-rag_blueprint}"

# MinIO configuration (use defaults, don't prompt)
MINIO_USER="${MINIO_USER:-minio_rag_user}"
MINIO_PASSWORD="${MINIO_PASSWORD:-minio_rag_password}"

# Export all variables for use by calling scripts
export HF_TOKEN
export TAVILY_API_KEY
export SERPAPI_API_KEY
export MAAS_API_BASE
export MAAS_API_KEY
export MAAS_MODEL_NAME
export POSTGRES_USER
export POSTGRES_PASSWORD
export POSTGRES_DBNAME
export MINIO_USER
export MINIO_PASSWORD
export KC_ADMIN_PASS
export APP_ADMIN_USERNAME
export APP_ADMIN_EMAIL
export APP_ADMIN_PASSWORD

# Also output them in a format that can be sourced
if [ "$1" = "--export" ]; then
    echo "export HF_TOKEN='$HF_TOKEN'"
    [ -n "$TAVILY_API_KEY" ] && echo "export TAVILY_API_KEY='$TAVILY_API_KEY'"
    [ -n "$SERPAPI_API_KEY" ] && echo "export SERPAPI_API_KEY='$SERPAPI_API_KEY'"
    [ -n "$MAAS_API_BASE" ] && echo "export MAAS_API_BASE='$MAAS_API_BASE'"
    [ -n "$MAAS_API_KEY" ] && echo "export MAAS_API_KEY='$MAAS_API_KEY'"
    [ -n "$MAAS_MODEL_NAME" ] && echo "export MAAS_MODEL_NAME='$MAAS_MODEL_NAME'"
    echo "export POSTGRES_USER='$POSTGRES_USER'"
    echo "export POSTGRES_PASSWORD='$POSTGRES_PASSWORD'"
    echo "export POSTGRES_DBNAME='$POSTGRES_DBNAME'"
    echo "export MINIO_USER='$MINIO_USER'"
    echo "export MINIO_PASSWORD='$MINIO_PASSWORD'"
    echo "export APP_ADMIN_USERNAME='$APP_ADMIN_USERNAME'"
    [ -n "$APP_ADMIN_EMAIL" ] && echo "export APP_ADMIN_EMAIL='$APP_ADMIN_EMAIL'"
    echo "export APP_ADMIN_PASSWORD='$APP_ADMIN_PASSWORD'"
fi

echo ""
echo "✅ Environment variables collected successfully!"
