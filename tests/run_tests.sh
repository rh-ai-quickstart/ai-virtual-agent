#!/bin/bash
# AI Virtual Agent Test Runner
set -e

# Generate unique identifier for this test run
export TAVERN_UNIQUE="test${RANDOM}"

# Pytest commands
PYTEST_CMD="pytest -n auto"
PYTEST_INTEG_CMD="pytest -n auto --dist loadfile"
PYTEST_OPTS="-W ignore::DeprecationWarning"

# Parse arguments
RUN_UNIT=false
RUN_INTEGRATION=false
SPECIFIC_TESTS=""

if [[ $# -eq 0 ]]; then
    RUN_UNIT=true
    RUN_INTEGRATION=true
else
    while [[ $# -gt 0 ]]; do
        case $1 in
            --unit) RUN_UNIT=true; shift ;;
            --integration) RUN_INTEGRATION=true; shift ;;
            --all) RUN_UNIT=true; RUN_INTEGRATION=true; shift ;;
            *) SPECIFIC_TESTS="$SPECIFIC_TESTS $1"; shift ;;
        esac
    done
fi

# Auto-detect test type from path
if [[ -n "$SPECIFIC_TESTS" ]]; then
    if [[ "$SPECIFIC_TESTS" == *"unit"* ]]; then
        RUN_UNIT=true; RUN_INTEGRATION=false
    elif [[ "$SPECIFIC_TESTS" == *"integration"* ]]; then
        RUN_UNIT=false; RUN_INTEGRATION=true
    else
        RUN_UNIT=false; RUN_INTEGRATION=false
    fi
fi

# Ensure PYTHONPATH includes project root
[[ ":$PYTHONPATH:" != *":.:"* ]] && export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}."

# Helper: Run pytest with error handling
run_pytest() {
    local test_path=$1
    local coverage_file=$2
    local pytest_cmd=$3

    if [ -n "$coverage_file" ]; then
        COVERAGE_FILE=$coverage_file $pytest_cmd $test_path -ra --cov=backend --cov-report= --cov-branch $PYTEST_OPTS || {
            echo "❌ Tests failed! Try: pip install -r tests/requirements.txt -r backend/requirements.txt"
            exit 1
        }
    else
        $pytest_cmd $test_path -v $PYTEST_OPTS || {
            echo "❌ Tests failed! Try: pip install -r tests/requirements.txt"
            exit 1
        }
    fi
}

echo "🧪 AI Virtual Agent Test Suite"
echo "====================================="

# Run unit tests
if [[ "$RUN_UNIT" == true ]]; then
    echo "🧪 Running unit tests..."
    export DISABLE_ATTACHMENTS=${DISABLE_ATTACHMENTS:-true}

    if [[ -n "$SPECIFIC_TESTS" ]]; then
        run_pytest "$SPECIFIC_TESTS" ".coverage.unit" "$PYTEST_CMD"
    else
        run_pytest "tests/unit" ".coverage.unit" "$PYTEST_CMD"
    fi
    echo "✅ Unit tests completed!"
fi

# Run integration tests
if [[ "$RUN_INTEGRATION" == true ]]; then
    # Check services
    echo "🔍 Checking services..."

    BACKEND_URL=${TEST_BACKEND_URL:-"http://localhost:8000"}
    FRONTEND_URL=${TEST_FRONTEND_URL:-"http://localhost:5173"}
    LLAMASTACK_URL=${TEST_LLAMASTACK_URL:-"http://localhost:8321"}

    services_ok=true
    for service in "Backend:$BACKEND_URL" "Frontend:$FRONTEND_URL" "LlamaStack:$LLAMASTACK_URL"; do
        name="${service%%:*}"
        url="${service#*:}"
        if curl -s "$url" > /dev/null 2>&1; then
            echo "✅ $name is running"
        else
            echo "❌ $name is not running at $url"
            services_ok=false
        fi
    done

    if [[ "$services_ok" == false ]]; then
        echo ""
        echo "❌ Services not running. Start with: ./deploy/local/scripts/start-dev.sh"
        exit 1
    fi

    export TEST_FRONTEND_URL="$FRONTEND_URL"
    export TEST_BACKEND_URL="$BACKEND_URL"
    export TEST_LLAMASTACK_URL="$LLAMASTACK_URL"

    echo "🚀 Running integration tests..."

    if [[ -n "$SPECIFIC_TESTS" ]]; then
        run_pytest "$SPECIFIC_TESTS" "" "$PYTEST_INTEG_CMD"
    else
        run_pytest "tests/integration/" "" "$PYTEST_INTEG_CMD"
    fi
    echo "✅ Integration tests completed!"

    # Extract coverage via HTTP
    echo "📊 Extracting integration coverage..."

    if curl -s -f "$BACKEND_URL/admin/coverage" -o .coverage.integration; then
        echo "✅ Coverage extracted"
    else
        echo "ℹ️  No integration coverage found"
    fi
fi

# Run specific tests (neither unit nor integration)
if [[ "$RUN_UNIT" == false && "$RUN_INTEGRATION" == false && -n "$SPECIFIC_TESTS" ]]; then
    echo "🚀 Running specified tests..."
    run_pytest "$SPECIFIC_TESTS" "" "$PYTEST_CMD"
fi

echo "✅ All tests completed!"

# Combine coverage
if [ -f ".coverage.unit" ] || [ -f ".coverage.integration" ]; then
    echo "📊 Combining coverage..."

    COVERAGE_FILES=""
    [ -f ".coverage.unit" ] && COVERAGE_FILES="$COVERAGE_FILES .coverage.unit"
    [ -f ".coverage.integration" ] && COVERAGE_FILES="$COVERAGE_FILES .coverage.integration"

    if [ -n "$COVERAGE_FILES" ]; then
        coverage combine $COVERAGE_FILES 2>/dev/null || true
        echo ""
        echo "📈 Coverage Report:"
        coverage report
        echo ""
        echo "💡 HTML report: coverage html && open htmlcov/index.html"
    fi
fi

echo ""
echo "Usage:"
echo "  ./run_tests.sh              # Run all tests"
echo "  ./run_tests.sh --unit       # Unit tests only"
echo "  ./run_tests.sh --integration # Integration tests only"
echo "  ./run_tests.sh tests/unit/test_specific.py  # Specific test"
