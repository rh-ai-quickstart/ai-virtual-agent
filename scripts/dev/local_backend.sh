#!/bin/bash

set -e # exit on error

echo $(pwd)

# Check if venv exists
if [ ! -d "venv" ]; then
  echo "❌ 'venv' directory not found. Please create a virtual environment first."
  exit 1
fi

echo "Starting Backend Server..."

source venv/bin/activate

cd backend
pre-commit install
alembic upgrade head
cd ..

./venv/bin/uvicorn backend.main:app --reload
