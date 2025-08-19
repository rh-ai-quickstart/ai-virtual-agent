#! /bin/bash

# Use same container runtime as other scripts, default to podman
CONTAINER_RUNTIME=${CONTAINER_RUNTIME:-podman}

SESSION_NAME="ai-virtual-agent-dev"

if tmux has-session -t $SESSION_NAME 2>/dev/null; then
    echo "Stopping development environment..."
    tmux kill-session -t $SESSION_NAME
    $CONTAINER_RUNTIME stop llama-server 2>/dev/null
    $CONTAINER_RUNTIME rm llama-server 2>/dev/null
    echo "Development environment stopped."
else
    echo "No development session found."
fi
