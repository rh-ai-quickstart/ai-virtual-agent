#!/bin/bash

# AI Virtual Agent - Development Environment Stop Script

set -e

# Change to project root directory
PROJECT_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$PROJECT_ROOT"
COMPOSE_FILE="$PROJECT_ROOT/deploy/local/compose.dev.yaml"

echo "🛑 Stopping AI Virtual Agent Development Environment..."

# Stop all services (including all profiles)
podman compose -f "$COMPOSE_FILE" --profile attachments down

echo "✅ All services stopped successfully"
echo ""
echo "💡 To remove all data (including database):"
echo "   podman compose -f \"$COMPOSE_FILE\" --profile attachments down --volumes"
echo ""
echo "🔄 To restart:"
echo "   make local/dev-compose-up"
