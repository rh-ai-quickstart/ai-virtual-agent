#! /bin/bash
set -e # exit on error

export DATABASE_URL=postgresql+asyncpg://admin:password@localhost:5432/ai_virtual_agent
# if you have LLamastack server deployed, you can use the following line:
# oc port-forward svc/llamastack 8321
export LLAMASTACK_URL=http://localhost:8321
# Here as well:
# oc port-forward svc/ds-pipeline-dspa 8888
export INGESTION_PIPELINE_URL=http://localhost:8888

# AI Virtual Agent Development Startup Script
# This script creates a tmux session with 3 windows for backend, llamastack, and frontend
# move between windows with ctrl+b, then the number of the window (0, 1, 2).

SESSION_NAME="ai-virtual-agent-dev"

# Check if tmux session already exists
if tmux has-session -t $SESSION_NAME 2>/dev/null; then
    echo "Session $SESSION_NAME already exists. Attaching to it..."
    tmux attach-session -t $SESSION_NAME
    exit 0
fi

# Create new tmux session with first window for backend
echo "Creating tmux session: $SESSION_NAME"
tmux new-session -d -s $SESSION_NAME -n "backend"

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Window 1: Backend
tmux send-keys -t $SESSION_NAME:backend "bash $SCRIPT_DIR/local_backend.sh" C-m



# Window 2: LlamaStack Server - Unmask if you don't have LLamastack deployed.
# tmux new-window -t $SESSION_NAME -n "llamastack"
# tmux send-keys -t $SESSION_NAME:llamastack "bash $SCRIPT_DIR/local_llamastack.sh" C-m


# Window 3: Frontend
tmux new-window -t $SESSION_NAME -n "frontend"
tmux send-keys -t $SESSION_NAME:frontend "bash $SCRIPT_DIR/local_frontend.sh" C-m


# Select the first window and attach to session
tmux select-window -t $SESSION_NAME:backend
tmux attach-session -t $SESSION_NAME
