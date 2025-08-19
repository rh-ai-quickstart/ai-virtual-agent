#!/bin/bash
set -e # exit on error

echo "Starting Frontend Dev Server..."

cd frontend

if [[ -d "node_modules" ]]; then
    echo "node_modules directory exists"
    rm -rf node_modules
    rm -rf node_modules/.vite
fi

npm install
npm run prepare


npm run dev
