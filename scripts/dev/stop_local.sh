#! /bin/bash

SESSION_NAME="ai-virtual-agent-dev"

if tmux has-session -t $SESSION_NAME 2>/dev/null; then
    echo "Stopping development environment..."
    tmux kill-session -t $SESSION_NAME
    podman stop llama-server 2>/dev/null
    podman rm llama-server 2>/dev/null
    echo "Development environment stopped."
else
    echo "No development session found."
fi
