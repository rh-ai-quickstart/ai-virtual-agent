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

# Admin user credentials (required for deployment)
ADMIN_USERNAME=$(prompt_for_value "ADMIN_USERNAME" "Enter admin user name")
ADMIN_EMAIL=$(prompt_for_value "ADMIN_EMAIL" "Enter admin user email")

# Tavily API Key (optional but recommended) - always show info
echo ""
echo "💡 Tavily Search API Key"
echo "     Without a key, web search capabilities will be disabled in your AI agents."
echo "     To enable web search, obtain a key from https://tavily.com/"
echo ""
TAVILY_API_KEY=$(prompt_for_value "TAVILY_API_KEY" "Enter Tavily API Key now (or press Enter to continue without web search)" "")

# Database configuration (use defaults, don't prompt)
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-rag_password}"
POSTGRES_DBNAME="${POSTGRES_DBNAME:-rag_blueprint}"

# MinIO configuration (use defaults, don't prompt)
MINIO_USER="${MINIO_USER:-minio_rag_user}"
MINIO_PASSWORD="${MINIO_PASSWORD:-minio_rag_password}"

# Export all variables for use by calling scripts
export HF_TOKEN
export ADMIN_USERNAME
export ADMIN_EMAIL
export TAVILY_API_KEY
export POSTGRES_USER
export POSTGRES_PASSWORD
export POSTGRES_DBNAME
export MINIO_USER
export MINIO_PASSWORD

# Also output them in a format that can be sourced
if [ "$1" = "--export" ]; then
    echo "export HF_TOKEN='$HF_TOKEN'"
    echo "export ADMIN_USERNAME='$ADMIN_USERNAME'"
    echo "export ADMIN_EMAIL='$ADMIN_EMAIL'"
    [ -n "$TAVILY_API_KEY" ] && echo "export TAVILY_API_KEY='$TAVILY_API_KEY'"
    echo "export POSTGRES_USER='$POSTGRES_USER'"
    echo "export POSTGRES_PASSWORD='$POSTGRES_PASSWORD'"
    echo "export POSTGRES_DBNAME='$POSTGRES_DBNAME'"
    echo "export MINIO_USER='$MINIO_USER'"
    echo "export MINIO_PASSWORD='$MINIO_PASSWORD'"
fi

echo ""
echo "✅ Environment variables collected successfully!"
