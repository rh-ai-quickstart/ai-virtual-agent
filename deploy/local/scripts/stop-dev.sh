#!/bin/bash

# AI Virtual Agent - Development Environment Stop Script

set -e

# Change to deploy/local directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_LOCAL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$DEPLOY_LOCAL_DIR"

echo "🛑 Stopping AI Virtual Agent Development Environment..."

# Stop all services (including all profiles)
podman compose --env-file ../../.env --profile attachments down

echo "✅ All services stopped successfully"
echo ""
echo "💡 To remove all data (including database):"
echo "   podman compose --env-file ../../.env --profile attachments down --volumes"
echo ""
echo "🔄 To restart:"
echo "   make compose-up"
