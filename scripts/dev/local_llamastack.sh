#!/bin/bash
set -e # exit on error

echo "Starting Local LlamaStack Server..."

cd "$(dirname "$0")/local_llamastack_server"
bash activate_llama_server.sh
