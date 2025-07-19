#!/bin/bash

echo "🚀 Deploying Standalone MCP Server for Demo..."

# Check if namespace exists
echo "📋 Checking namespace..."
kubectl get namespace ai-assistant > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Namespace 'ai-assistant' not found!"
    echo "Please create it first: kubectl create namespace ai-assistant"
    exit 1
fi

# Deploy MCP server
echo "📦 Deploying MCP server..."
kubectl apply -f mcp-dbstore-standalone.yaml

# Wait for deployment to be ready
echo "⏳ Waiting for MCP server to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/mcp-dbstore-standalone -n ai-assistant

# Check status
echo "✅ Checking deployment status..."
kubectl get pods -n ai-assistant | grep mcp-dbstore
kubectl get services -n ai-assistant | grep mcp-dbstore

# Check logs
echo "📋 Checking MCP server logs..."
kubectl logs -n ai-assistant deployment/mcp-dbstore-standalone --tail=10

echo "🎉 MCP Server deployment complete!"
echo "Service URL: mcp-dbstore-standalone:8002"
echo "Ready for demo! 🚀" 