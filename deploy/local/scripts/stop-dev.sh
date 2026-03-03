#!/bin/bash

# AI Virtual Agent - Development Environment Stop Script

set -e

# Change to deploy/local directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEPLOY_LOCAL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$DEPLOY_LOCAL_DIR"

echo "🛑 Stopping AI Virtual Agent Development Environment..."

# Stop all services (including all profiles and orphaned containers)
podman compose --env-file "$PROJECT_ROOT/.env" --profile attachments down --remove-orphans

# Force-remove any leftover containers that compose failed to clean up.
# This handles cases where podman loses track of compose-managed containers.
DEV_CONTAINERS=(
    postgresql-dev ollama-dev llamastack-dev
    ai-va-backend-dev ai-va-frontend-dev
    travel-research-mcp-dev hotel-mcp-dev flight-mcp-dev
    minio-dev
)
for ctr in "${DEV_CONTAINERS[@]}"; do
    podman rm -f "$ctr" 2>/dev/null || true
done

echo "✅ All services stopped successfully"
echo ""
echo "💡 To remove all data (including database):"
echo "   podman compose --profile attachments down --volumes"
echo ""
echo "🔄 To restart:"
echo "   make compose-up"
