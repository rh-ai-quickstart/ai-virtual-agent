#!/bin/bash

# AI Virtual Agent Test Runner
set -e

echo "🧪 AI Virtual Agent Test Suite"
echo "====================================="

# Parse command line arguments
RUN_UNIT=false
RUN_INTEGRATION=false
SPECIFIC_TESTS=""

# Default to running both if no arguments
if [[ $# -eq 0 ]]; then
    RUN_UNIT=true
    RUN_INTEGRATION=true
else
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --unit)
                RUN_UNIT=true
                shift
                ;;
            --integration)
                RUN_INTEGRATION=true
                shift
                ;;
            --all)
                RUN_UNIT=true
                RUN_INTEGRATION=true
                shift
                ;;
            *)
                # Assume it's a specific test file/pattern
                SPECIFIC_TESTS="$SPECIFIC_TESTS $1"
                shift
                ;;
        esac
    done
fi

# If specific tests are provided, determine type based on path
if [[ -n "$SPECIFIC_TESTS" ]]; then
    if [[ "$SPECIFIC_TESTS" == *"unit"* ]]; then
        RUN_UNIT=true
        RUN_INTEGRATION=false
    elif [[ "$SPECIFIC_TESTS" == *"integration"* ]]; then
        RUN_UNIT=false
        RUN_INTEGRATION=true
    else
        # Default to running the specific test without type detection
        RUN_UNIT=false
        RUN_INTEGRATION=false
    fi
fi

# Default URLs (can be overridden by environment variables)
FRONTEND_URL=${TEST_FRONTEND_URL:-"http://localhost:5173"}
BACKEND_URL=${TEST_BACKEND_URL:-"http://localhost:8000"}
LLAMASTACK_URL=${TEST_LLAMASTACK_URL:-"http://localhost:8321"}

echo "🔧 Configuration:"
echo "  For postgresql server run: podman compose --file compose.yaml up --detach"
echo "  Frontend URL: $FRONTEND_URL"
echo "  Backend URL: $BACKEND_URL"
echo "  LlamaStack URL: $LLAMASTACK_URL"
echo ""

# Check if we're already in a virtual environment
if [[ -z "$VIRTUAL_ENV" ]] && [[ -z "$CONDA_DEFAULT_ENV" ]]; then
    echo "⚠️  Warning: Not running in a virtual environment!"
    echo "   It's recommended to activate a virtual environment or conda environment before running tests."
    echo ""
fi

# Run unit tests first (they don't need services)
if [[ "$RUN_UNIT" == true ]]; then
    echo ""
    echo "🧪 Running unit tests..."
    echo "------------------------"
    if [[ -n "$SPECIFIC_TESTS" ]]; then
        pytest $SPECIFIC_TESTS -ra --cov=backend --cov-report=term-missing --cov-branch || {
            echo ""
            echo "❌ Unit tests failed!"
            echo "   If you see pytest not found or import errors, try: pip install -r requirements-test.txt -r backend/requirements.txt"
            exit 1
        }
    else
        pytest tests/unit -ra --cov=backend --cov-report=term-missing --cov-branch || {
            echo ""
            echo "❌ Unit tests failed!"
            echo "   If you see pytest not found or import errors, try: pip install -r requirements-test.txt -r backend/requirements.txt"
            exit 1
        }
    fi
    echo ""
    echo "✅ Unit tests completed!"
fi

# Only check services if we're running integration tests
if [[ "$RUN_INTEGRATION" == true ]]; then

# Check if services are running
echo "🔍 Checking if services are running..."

# Function to check service
check_service() {
    local name=$1
    local url=$2

    if curl -s "$url" > /dev/null 2>&1; then
        echo "✅ $name is running at $url"
        return 0
    else
        echo "❌ $name is not running at $url"
        return 1
    fi
}

# Check all services
services_ok=true

if ! check_service "Backend" "$BACKEND_URL"; then
    services_ok=false
fi

if ! check_service "Frontend" "$FRONTEND_URL"; then
    services_ok=false
fi

if ! check_service "LlamaStack" "$LLAMASTACK_URL"; then
    services_ok=false
fi

# Exit if services are not running
if [[ "$services_ok" == false ]]; then
    echo ""
    echo "❌ Some services are not running. Please start them before running tests."
    echo ""
    echo "To start the services, run:"
    echo "  ./scripts/dev/run_local.sh"
    echo ""
    echo "Or start them individually:"
    echo "  1. podman compose --file compose.yaml up --detach"
    echo "  2. Backend: cd backend && python -m uvicorn main:app --reload --port 8000"
    echo "  3. Frontend: cd frontend && npm run dev"
    echo "  4. LlamaStack: cd scripts/dev/local_llamastack_server && ./activate_llama_server.sh"
    echo ""
    echo "Then run the tests again:"
    echo "  ./run_tests.sh"
    echo ""
    exit 1
fi

echo ""
echo "✅ All services are running!"
echo ""

# Export environment variables for tests
export TEST_FRONTEND_URL="$FRONTEND_URL"
export TEST_BACKEND_URL="$BACKEND_URL"
export TEST_LLAMASTACK_URL="$LLAMASTACK_URL"

    # Run integration tests
    echo "🚀 Running integration tests..."
    echo "------------------------------"

    if [[ -n "$SPECIFIC_TESTS" ]]; then
        pytest $SPECIFIC_TESTS -v || {
            echo ""
            echo "❌ Integration tests failed!"
            echo "   If you see import errors, try: pip install -r requirements-test.txt"
            exit 1
        }
    else
        pytest tests/integration/ -v || {
            echo ""
            echo "❌ Integration tests failed!"
            echo "   If you see import errors, try: pip install -r requirements-test.txt"
            exit 1
        }
    fi
    echo ""
    echo "✅ Integration tests completed!"
fi

# Run specific tests if neither unit nor integration was explicitly chosen
if [[ "$RUN_UNIT" == false && "$RUN_INTEGRATION" == false && -n "$SPECIFIC_TESTS" ]]; then
    echo "🚀 Running specified tests..."
    pytest $SPECIFIC_TESTS -v || {
        echo ""
        echo "❌ Tests failed!"
        echo "   If you see import errors, try: pip install -r requirements-test.txt"
        exit 1
    }
fi

echo ""
echo "✅ All tests completed successfully!"
echo ""
echo "Usage:"
echo "  ./run_tests.sh              # Run all tests (unit + integration)"
echo "  ./run_tests.sh --unit       # Run only unit tests"
echo "  ./run_tests.sh --integration # Run only integration tests"
echo "  ./run_tests.sh --all        # Run all tests (same as no args)"
echo "  ./run_tests.sh tests/unit/test_specific.py  # Run specific test file"
