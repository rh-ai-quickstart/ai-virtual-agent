# AI Virtual Agent Test Suite

This directory contains both unit and integration tests for the AI Virtual Agent application.

## Test Types

### Unit Tests (`tests/unit/`)
- Test individual backend modules and functions in isolation
- Run quickly without requiring external services
- Include code coverage reporting
- Import and test backend code directly

### Integration Tests (`tests/integration/`)
- Test end-to-end functionality across services
- Require all services (Backend, Frontend, LlamaStack) to be running
- Use HTTP requests to test API endpoints
- Validate real service interactions

## Quick Start

### Unit Tests Only

```bash
# Run unit tests (no services required)
./run_tests.sh --unit
```

### 1. Start Services Manually

For integration tests, first start all required services:
Follow the steps in [Conribution](../CONTRIBUTING.md)

Make sure that the only model served is `llama3.2:3b-instruct-fp16`

### 2. Run Integration Tests

Once services are running:

```bash
# Run only integration tests
./run_tests.sh --integration

# Run specific test file
./run_tests.sh tests/integration/test_chat_pipeline.tavern.yaml

# Run specific Tavern test file
./run_tests.sh tests/integration/test_chat_pipeline.tavern.yaml

# Run with custom configuration
TEST_FRONTEND_URL="http://localhost:3000" ./run_tests.sh --integration
```

### 3. Run All Tests

```bash
# Run both unit and integration tests
./run_tests.sh

# Or explicitly
./run_tests.sh --all
```

## Test Configuration

### Environment Variables

Configure test URLs using environment variables:

```bash
# Development (default)
export TEST_FRONTEND_URL="http://localhost:5173"
export TEST_BACKEND_URL="http://localhost:8000"
export TEST_LLAMASTACK_URL="http://localhost:8321"

# Custom configuration
export TEST_FRONTEND_URL="http://localhost:3000"
export TEST_BACKEND_URL="http://localhost:8080"
export TEST_LLAMASTACK_URL="http://localhost:8888"
```

### Podman/Container Setup

For containerized environments:

```bash
export TEST_FRONTEND_URL="http://frontend:5173"
export TEST_BACKEND_URL="http://backend:8000"
export TEST_LLAMASTACK_URL="http://llamastack:8321"
```

## Running Tests

### Unit Tests

Unit tests run quickly and don't require any services:

```bash
# Run all unit tests with coverage
./run_tests.sh --unit

# Run specific unit test file
./run_tests.sh tests/unit/test_llamastack_endpoints.py
```

### Integration Tests

Integration tests require all services to be running before executing:

```bash
# Run all integration tests (services must be running)
./run_tests.sh --integration

# Run with custom configuration
TEST_FRONTEND_URL="http://localhost:3000" ./run_tests.sh --integration
```

### All Tests

```bash
# Run both unit and integration tests
./run_tests.sh
./run_tests.sh --all
```

### Specific Tests

```bash
# Run specific test file
./run_tests.sh tests/integration/test_chat_pipeline.tavern.yaml

# Run with pattern
./run_tests.sh tests/integration/test_specific_*

# Run with pytest options
./run_tests.sh \"tests/integration/test_endpoints.tavern.yaml::Test Models API Endpoint\"
```

## Available Commands

### Script Commands

```bash
./run_tests.sh              # Run all tests (unit + integration)
./run_tests.sh --unit       # Run only unit tests
./run_tests.sh --integration # Run only integration tests
./run_tests.sh --all        # Run all tests (same as no args)
./run_tests.sh tests/unit/test_specific.py  # Run specific test file
```

## Service Management

### Unit Tests

Unit tests don't require any services and will automatically install backend dependencies.

### Manual Service Management

Integration tests require all services to be running before executing:

- **Backend**: `http://localhost:8000` (or `$TEST_BACKEND_URL`)
- **Frontend**: `http://localhost:5173` (or `$TEST_FRONTEND_URL`)
- **LlamaStack**: `http://localhost:8321` (or `$TEST_LLAMASTACK_URL`)

### Service Verification

For integration tests, the script checks if services are running and provides helpful instructions if they're not:

```bash
🔍 Checking if services are running...
✅ Backend is running at http://localhost:8000
✅ Frontend is running at http://localhost:5173
✅ LlamaStack is running at http://localhost:8321
```

If any service is not running, the script will exit with clear instructions on how to start them.

## Test Structure

### Test Files

**Unit Tests (Python-based):**
- `test_llamastack_endpoints.py` - Backend API endpoint unit tests
- `test_mcp_llamastack.py` - MCP LlamaStack integration unit tests

**Tavern Tests (YAML-based):**
- `test_chat_pipeline.tavern.yaml` - End-to-end chat functionality with response validation
- `test_models_api.tavern.yaml` - API endpoint testing with structured validation
- `test_llama_stack_api.tavern.yaml` - LlamaStack service integration tests

**Shared Resources:**
- `validators.py` - Custom validation functions for both Python and Tavern tests

## Dependencies

### Dependency Management

Dependencies are installed automatically based on test type:

- **Unit tests**: Install both `requirements-test.txt` and `backend/requirements.txt`
- **Integration tests**: Install only `requirements-test.txt`
- **All tests**: Install both dependency sets

### Test Dependencies (`requirements-test.txt`)

```
pytest>=7.0.0
pydantic[email]
tavern>=2.0.0
requests>=2.25.0
pyyaml>=6.0
jsonschema>=4.0.0
pytest-cov>=4.1
```

### Backend Dependencies

Unit tests automatically install backend dependencies from `backend/requirements.txt` to import backend modules.

## CI/CD Integration

The test runner is designed to work in CI/CD environments where services are pre-started:

```bash
# GitLab CI example
before_script:
  - ./scripts/dev/run_local.sh &
  - sleep 30  # Wait for services to start
script:
  - ./run_tests.sh --all

# GitHub Actions example
- name: Start Services
  run: ./scripts/dev/run_local.sh &
- name: Wait for Services
  run: sleep 30
- name: Run All Tests
  run: ./run_tests.sh --all
```

For CI environments that want to run tests separately:

```bash
# Run unit tests first (fast, no services needed)
- name: Run Unit Tests
  run: ./run_tests.sh --unit

# Then start services and run integration tests
- name: Start Services
  run: ./local_dev/run_local.sh &
- name: Wait for Services
  run: sleep 30
- name: Run Integration Tests
  run: ./run_tests.sh --integration
```

For more detailed configuration options, see [Config](CONFIG.md).
