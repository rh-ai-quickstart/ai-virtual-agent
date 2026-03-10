# AI Virtual Agent - Local Development Makefile
# Run `make help` to see available targets.

.PHONY: help \
        lint lint-backend lint-frontend test test-unit test-int \
        compose-up compose-down compose-restart \
        compose-logs compose-build compose-status image-build

# -----------------------------------------------------------------------------
# Helper
# -----------------------------------------------------------------------------
help: ## Show help for local development targets
	@echo "AI Virtual Agent - Local Development Commands"
	@echo "============================================="
	@echo ""
	@echo "🔧 Local Container Commands:"
	@grep -E '^(compose-up|compose-down|compose-restart|compose-logs|compose-build|compose-status):.*?## ' $(MAKEFILE_LIST) | \
		sed -e 's/^/  /' -e 's/:.*## / - /'
	@echo "🧪 Testing & Quality:"
	@grep -E '^(test|test-unit|test-int|lint|lint-backend|lint-frontend):.*?## ' $(MAKEFILE_LIST) | \
		sed -e 's/^/  /' -e 's/:.*## / - /'
	@echo ""


# -----------------------------------------------------------------------------
# Quality & Tests
# -----------------------------------------------------------------------------
lint-backend: ## Run backend linters (pre-commit)
	cd ../../backend && pre-commit run --all-files --show-diff-on-failure || true

lint-frontend: ## Run frontend linters (eslint & prettier)
	cd ../../frontend && npm run lint

lint: lint-backend lint-frontend ## Run all linters

test-unit: ## Run unit tests only
	cd ../../ && ./tests/run_tests.sh --unit

test-int: ## Run integration tests only
	cd ../../ && ./tests/run_tests.sh --integration

test-all: ## Run all tests (unit + integration)
	cd ../../ && ./tests/run_tests.sh --all

test: lint test-all ## Run full test & lint suite

# -----------------------------------------------------------------------------
# Container / Compose helpers
# -----------------------------------------------------------------------------
compose-up: ## Start development services with podman compose (uses .env and compose.dev.yaml)
	./scripts/start-dev.sh

compose-down: ## Stop development services
	./scripts/stop-dev.sh

compose-restart: ## Restart development services
	podman compose --env-file ../../.env -f compose.yaml restart

compose-logs: ## View logs from development services
	podman compose --env-file ../../.env -f compose.yaml logs -f

compose-build: ## Rebuild and start development services
	podman compose --env-file ../../.env -f compose.yaml up --build -d

compose-status: ## Show status of development services
	podman compose --env-file ../../.env -f compose.yaml ps
