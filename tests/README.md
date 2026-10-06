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

### Browser UI Tests (`tests/ui/`)
- Use Playwright and Chromium to exercise the rendered application in a browser
- Run in an isolated `uv` project environment; no global Python packages are installed
- Save a screenshot after each test under `tests/ui/screenshots/` by default
- Require the application UI to be reachable at `TEST_FRONTEND_URL`
- Cover mocked administration and error states, plus live agent inference,
  template deployment, ingestion, MCP tools, attachments, and user permissions

The knowledge-base browser CRUD flow intercepts its API calls so it can test the
UI without creating vector stores or ingestion pipelines in the test namespace. Live
browser tests use the real API and clean up the temporary records they create. Admin
flows require an authenticated admin account. The live RAG tests check both the
chart's seeded default pipeline and a separately created knowledge base by querying
retrieved passage text through real chat inference.

## Mocked and Live Coverage

The suite keeps mocks for repeatable validation, cancellation, error, and empty-state
checks. The following live tests exercise configured backend services:

| Test file | Service path exercised | Mocking |
| --- | --- | --- |
| `tests/ui/test_live_agent_inference.py` | Browser agent creation, sampling settings, assignment, chat UI, and live inference | None |
| `tests/ui/test_live_template_chat.py` | Template API deployment, template-suite deployment dialog, user-agent assignment, browser chat UI, LlamaStack inference, session persistence | None |
| `tests/ui/test_live_user_management.py` | Browser create, edit, and delete against the users API and database | None |
| `tests/ui/test_live_auth_permissions.py` | Real user identity, protected admin UI, and denied users API operations | None |
| `tests/ui/test_live_knowledge_base_chat.py` | Knowledge-base ingestion, retrieval, and grounded chat with live LlamaStack inference | None; uses the deployment's sample PDF by default, with optional source overrides |
| `tests/ui/test_live_default_ingestion_pipeline.py` | Seeded default S3 pipeline readiness, indexed sample retrieval, and grounded browser chat | None; uses the chart's `zippity-zoo-vector-db` vector store |
| `tests/ui/test_live_mcp_tool.py` | MCP discovery and registration, real travel tool execution, and chat inference | None; uses the discovered `mcp-travel-research` service |
| `tests/ui/test_live_attachments.py` | Real attachment upload, object storage retrieval, and session cleanup | None; does not call inference or require a vision model |
| `tests/integration/test_live_template_chat.py` | Template deployment, chat session API, inference, persisted messages | None |
| `tests/integration/*.tavern.yaml` | HTTP integration coverage against the configured backend/frontend APIs; chat pipeline cases call live inference | None |

The following Playwright files intercept API calls for isolated UI behavior:

| Test file | Coverage |
| --- | --- |
| `tests/ui/test_agent_management.py` | Agent form validation, CRUD, and confirmation flows |
| `tests/ui/test_agent_templates.py` | Template selection, overrides, failure reporting, and a mocked deploy-then-chat flow (`test_mocked_deployed_template_agent_can_chat`) |
| `tests/ui/test_chat_sessions.py` | Chat session, tool trace, streaming, and error states |
| `tests/ui/test_knowledge_bases.py` | Knowledge-base forms, validation, and mocked CRUD |
| `tests/ui/test_mcp_servers.py` | MCP discovery, validation, CRUD, and API errors |
| `tests/ui/test_model_providers.py` | Provider configuration, errors, and empty states |
| `tests/ui/test_user_management.py` | Mocked user creation, profile changes, assignments, and permissions |

`tests/ui/test_smoke.py` checks navigation and theme behavior in the browser; it does
not validate backend inference. Unit tests isolate backend code and use test doubles
where external services or persistence would otherwise be required.

### Live UI Test Prerequisites

The live knowledge-base ingestion test uses the deployment's sample PDF by default
and checks that the assistant repeats text retrieved from the source. It uses the
E2E chart's default embedding model and pgvector provider, so it does not require a
pre-existing ingested knowledge base or the version-sensitive embedding-model listing
endpoint. Override these values for deployments with different settings. You can also
override the source and optionally require a particular phrase:

```bash
export TEST_KB_SOURCE_URL="https://your-test-host.example/live-kb-fixture.txt"
export TEST_KB_EXPECTED_TEXT="a distinctive phrase in the fixture"
export TEST_KB_EMBEDDING_MODEL="your-embedding-model"
export TEST_KB_VECTOR_PROVIDER="your-vector-provider"
```

The E2E OpenShift install enables the chart's default S3 ingestion pipeline. Its live
test waits for the seeded vector store and verifies retrieval and grounded chat using
the sample PDF uploaded to the `documents` bucket.

The MCP test uses the `mcp-travel-research` service discovered from Kubernetes. The
E2E deployment must have this service enabled and reachable by LlamaStack. The live
attachment test uses the configured S3-compatible attachment store to verify upload,
download, and deletion with a `.txt` file; it does not send the file to a model.
The auth test creates a temporary non-admin account and uses its forwarded identity
headers, so run it in the test/development authentication setup. To avoid skips in a
live run, provide an authenticated admin, a served inference model, the
travel-research MCP service, and working attachment object storage.

## Quick Start

### Using Makefile Commands (Recommended)

Use the local Makefile for unit and full local suites, and the cluster Makefile for
the integration entry point. The cluster target supplies the Tavern dependencies
through an isolated `uv` environment:

```bash
# Run unit tests only
make -C deploy/local test-unit

# Run integration tests only
make -C deploy/cluster test-int

# Run all tests (unit + integration)
make -C deploy/local test-all

# Run linters and all tests
make -C deploy/local test
```

`make -C deploy/cluster test-int` runs the Tavern integration tests and then the
Playwright UI tests. `uv` supplies the Tavern dependencies in an isolated
environment; the UI runner manages its own `tests/ui/.venv`. Playwright downloads
Chromium if its browser binary is missing.
Screenshots are written to `tests/ui/screenshots/` and ignored by Git. Set
`UI_SCREENSHOT_DIR` to save them elsewhere.

Run only the browser tests with:

```bash
./tests/ui/run_ui_tests.sh
```

For a local development setup, the default UI URL is `http://127.0.0.1:5173`.
For the OpenShift E2E deployment, the existing `TEST_FRONTEND_URL` points to the
port-forwarded application, where the built UI is served from the backend.
The default-ingestion, knowledge-base-ingestion, and live MCP-tool UI tests need
cluster resources and are skipped locally. The OpenShift E2E runner sets
`TEST_E2E_DEPLOYMENT=true` so those tests run there.

### Unit Tests Only

```bash
# Run unit tests (no services required)
./run_tests.sh --unit

# Or using Makefile
make -C deploy/local test-unit
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

# Or using Makefile
make -C deploy/cluster test-int

# Run specific test file
./run_tests.sh tests/integration/test_chat_pipeline.tavern.yaml

# Run specific Tavern test file
./run_tests.sh tests/integration/test_chat_pipeline.tavern.yaml

# Run with custom configuration
TEST_FRONTEND_URL="http://localhost:3000" ./run_tests.sh --integration
```

### Run Against an OpenShift E2E Installation

From the quickstart root, install the test deployment with an OpenAI-compatible
inference endpoint. `LLM_URL` is the endpoint base URL ending in `/v1`, and
`LLM_ID` is the model identifier served by that endpoint:

```bash
make -C deploy/cluster install-e2e-openshift \
  NAMESPACE=ai-virtual-agent-e2e \
  LLM=your-model-key \
  LLM_URL="https://your-inference.example.com/v1" \
  LLM_ID="your-model-id" \
  LLM_API_TOKEN="your-api-token"
```

The target enables local development authentication only in this dedicated E2E
namespace, registers the remote model instead of deploying an inference pod, and
starts the backend and LlamaStack port-forwards. Run the integration suite with:

```bash
make -C deploy/cluster test-int
```

This requires `oc` logged into the cluster, Helm, and `uv`; `uv` installs the
Python test dependencies from `tests/requirements.txt` in an isolated environment.
The integration tests create and
delete test users, agents, and sessions; use a disposable test namespace. Stop
the forwards and uninstall the E2E deployment after testing with:

```bash
make -C deploy/cluster uninstall-e2e-openshift
```

### 3. Run All Tests

```bash
# Run both unit and integration tests
./run_tests.sh

# Or explicitly
./run_tests.sh --all

# Or using Makefile
make -C deploy/local test-all

# Run all tests with linting
make -C deploy/local test
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

### Makefile Commands

From the project root directory:

```bash
make -C deploy/local test-unit     # Run only unit tests
make -C deploy/cluster test-int    # Run integration and browser tests
make -C deploy/local test-all      # Run all local tests (unit + integration)
make -C deploy/local test          # Run linters and all local tests
make -C deploy/local lint          # Run all linters
make -C deploy/local lint-backend  # Run backend linters only
make -C deploy/local lint-frontend # Run frontend linters only
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

- **Unit tests**: Install both `tests/requirements.txt` and `backend/requirements.txt`
- **Integration tests**: Install only `tests/requirements.txt`
- **All tests**: Install both dependency sets

### Test Dependencies (`tests/requirements.txt`)

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
  # Use the new containerized development setup
  - sleep 30  # Wait for services to start
script:
  - ./run_tests.sh --all
  # Or using Makefile
  - make -C deploy/local test-all

# GitHub Actions example
- name: Start Services
  # Use make compose-up for containerized development
- name: Wait for Services
  run: sleep 30
- name: Run All Tests
  run: ./run_tests.sh --all
  # Or using Makefile
  # run: make -C deploy/local test-all
```

For CI environments that want to run tests separately:

```bash
# Run unit tests first (fast, no services needed)
- name: Run Unit Tests
  run: ./run_tests.sh --unit
  # Or using Makefile
  # run: make -C deploy/local test-unit

# Then start services and run integration tests
- name: Start Services
  # Use make compose-up for containerized development
- name: Wait for Services
  run: sleep 30
- name: Run Integration Tests
  run: ./run_tests.sh --integration
  # Or using Makefile
  # run: make -C deploy/cluster test-int
```

For more detailed configuration options, see [Config](CONFIG.md).
