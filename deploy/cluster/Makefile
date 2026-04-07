# AI Virtual Agent - Helm Deployment Makefile
# Run `make help` to see available targets.

.PHONY: help install install-help install-status deps uninstall install-namespace list-models list-mcps \
       build-mcp-images push-mcp-images

# -----------------------------------------------------------------------------
# Helper
# -----------------------------------------------------------------------------
help: ## Show help for helm deployment targets
	@echo "AI Virtual Agent - Helm Deployment Commands"
	@echo "==========================================="
	@echo ""
	@echo "☸️  Deployment Commands:"
	@grep -E '^(install|install-help|install-status|deps|uninstall|list-models|list-mcps|build-mcp-images|push-mcp-images):.*?## ' $(MAKEFILE_LIST) | \
		sed -e 's/^/  /' -e 's/:.*## / - /'
	@echo ""
	@echo "For detailed deployment help, run: make install-help"

# -----------------------------------------------------------------------------
# Deployment (Helm/OpenShift)
# -----------------------------------------------------------------------------

# Helm deployment configuration variables
NAMESPACE ?=
POSTGRES_USER ?= postgres
POSTGRES_PASSWORD ?= rag_password
POSTGRES_DBNAME ?= rag_blueprint
MINIO_USER ?= minio_rag_user
MINIO_PASSWORD ?= minio_rag_password
HF_TOKEN ?=
ORACLE ?= false
AI_VIRTUAL_AGENT_CHART := helm
AI_VIRTUAL_AGENT_RELEASE := ai-virtual-agent
TOLERATIONS_TEMPLATE=[{"key":"$(1)","effect":"NoSchedule","operator":"Exists"}]

# Ingestion pipeline configuration
SOURCE ?= S3
EMBEDDING_MODEL ?= all-MiniLM-L6-v2
INGESTION_PIPELINE_NAME ?= demo-rag-vector-db
INGESTION_PIPELINE_VERSION ?= 1.0
ACCESS_KEY_ID ?= $(MINIO_USER)
SECRET_ACCESS_KEY ?= $(MINIO_PASSWORD)
BUCKET_NAME ?= documents
ENDPOINT_URL ?= http://minio:9000
REGION ?= us-east-1
AUTH_INGESTION_PIPELINE_USER ?= ingestion-pipeline

# Check namespace is set only for deployment commands that need it
ifneq (,$(filter install install-status uninstall install-namespace,$(MAKECMDGOALS)))
ifeq ($(NAMESPACE),)
$(error NAMESPACE is not set. Use: make <target> NAMESPACE=<your-namespace>)
endif
endif

install-help: ## Show detailed deployment help and configuration options
	@echo "AI Virtual Agent Deployment Help"
	@echo "================================"
	@echo ""
	@echo "Available deployment targets:"
	@echo "  install          - Install the AI Virtual Agent deployment"
	@echo "  install-status   - Check deployment status"
	@echo "  uninstall        - Uninstall deployment and clean up resources"
	@echo "  deps             - Update Helm dependencies"
	@echo ""
	@echo "Required Configuration:"
	@echo "  NAMESPACE        - Target namespace (required for all deployment commands)"
	@echo ""
	@echo "Optional Configuration (set via environment variables or will be prompted):"
	@echo "  HF_TOKEN                 - Hugging Face Token"
	@echo "  TAVILY_API_KEY           - Tavily Search API Key"
	@echo "  SERPAPI_API_KEY          - SerpApi API Key (hotel/flight search)"
	@echo "  ADMIN_USERNAME           - Admin user name"
	@echo "  ADMIN_EMAIL              - Admin user email"
	@echo "  {SAFETY,LLM}             - Model id as defined in values (eg. llama-3-2-1b-instruct)"
	@echo "  {SAFETY,LLM}_ID          - Model identifier override (defaults to model key name)"
	@echo "  {SAFETY,LLM}_URL         - Model URL"
	@echo "  {SAFETY,LLM}_API_TOKEN   - Model API token for remote models"
	@echo "  {SAFETY,LLM}_TOLERATION  - Model pod toleration"
	@echo ""
	@echo "MaaS / Runner LLM Configuration:"
	@echo "  MAAS_API_BASE            - MaaS endpoint base URL (used by LangGraph & CrewAI)"
	@echo "  MAAS_API_KEY             - MaaS API key"
	@echo "  MAAS_MODEL_NAME          - MaaS model name"
	@echo "  LANGGRAPH_LLM_API_BASE   - Override LangGraph LLM base URL"
	@echo "  CREWAI_LLM_API_BASE      - Override CrewAI LLM base URL"
	@echo ""
	@echo "Example usage:"
	@echo "  make install NAMESPACE=my-ai-assistant"
	@echo "  make install-status NAMESPACE=my-ai-assistant"

deps: ## Update Helm dependencies
	@echo "Updating Helm dependencies"
	@helm dependency update $(AI_VIRTUAL_AGENT_CHART) &> /dev/null

list-models: deps ## List available models
	@helm template dummy-release $(AI_VIRTUAL_AGENT_CHART) --set llm-service._debugListModels=true | grep ^model:

list-mcps: deps
	@helm template dummy-release $(AI_VIRTUAL_AGENT_CHART) --set mcp-servers._debugListMcps=true | grep ^MCP

install-namespace: ## Create and configure deployment namespace
	@oc create namespace $(NAMESPACE) &> /dev/null && oc label namespace $(NAMESPACE) modelmesh-enabled=false ||:
	@oc project $(NAMESPACE) &> /dev/null ||:

install: install-namespace deps ## Install the AI Virtual Agent deployment
	@./scripts/install_with_env.sh $(NAMESPACE) $(AI_VIRTUAL_AGENT_RELEASE) $(AI_VIRTUAL_AGENT_CHART)

	@echo "Waiting for model services and llamastack to deploy. It may take around 10-15 minutes depending on the size of the model..."
	@oc rollout status deploy/ai-virtual-agent -n $(NAMESPACE)
	@if [ "$(ORACLE)" = "true" ]; then \
		echo "Oracle enabled - waiting for TPC-DS data population to complete. This may take some time..."; \
		oc wait --for=condition=complete --timeout=3600s job/oracle-db-tpcds-populate -n $(NAMESPACE); \
	fi
	@echo "$(AI_VIRTUAL_AGENT_RELEASE) installed successfully"
	@echo ""
	@echo "Getting application URL..."
	@APP_URL=$$(oc get route ai-virtual-agent-authenticated -n $(NAMESPACE) -o jsonpath='{.status.ingress[0].host}' 2>/dev/null || echo ""); \
	if [ -n "$$APP_URL" ]; then \
		echo "🎉 Application is ready!"; \
		echo "📱 Access your AI Virtual Agent at: https://$$APP_URL"; \
	else \
		echo "⚠️  Route not ready yet. Get the URL manually with:"; \
		echo "   oc get route ai-virtual-agent-authenticated -n $(NAMESPACE)"; \
	fi
	@echo ""

uninstall: ## Uninstall deployment and clean up resources
	@echo "Uninstalling $(AI_VIRTUAL_AGENT_RELEASE) helm chart from namespace $(NAMESPACE)"
	@helm uninstall --ignore-not-found $(AI_VIRTUAL_AGENT_RELEASE) -n $(NAMESPACE)
	@echo "Removing pgvector and minio PVCs from $(NAMESPACE)"
	@oc get pvc -n $(NAMESPACE) -o custom-columns=NAME:.metadata.name | grep -E '^(pg|minio|oracle)-data' | xargs -I {} oc delete pvc -n $(NAMESPACE) {} ||:
	@echo "Deleting remaining pods in namespace $(NAMESPACE)"
	@oc delete pods -n $(NAMESPACE) --all
	@echo "Checking for any remaining resources in namespace $(NAMESPACE)..."
	@echo "If you want to completely remove the namespace, run: oc delete project $(NAMESPACE)"
	@echo "Remaining resources in namespace $(NAMESPACE):"
	@$(MAKE) install-status NAMESPACE=$(NAMESPACE)

# -----------------------------------------------------------------------------
# MCP Server Images
# -----------------------------------------------------------------------------
CONTAINER_RUNTIME ?= podman
MCP_IMAGE_REGISTRY ?= quay.io/skattoju
MCP_IMAGE_TAG ?= latest
MCP_SERVERS := travel_research_mcp hotel_mcp flight_mcp

build-mcp-images: ## Build container images for vacation-planner MCP servers
	@for server in $(MCP_SERVERS); do \
		img_name=$$(echo "mcp-$$server" | sed 's/_mcp$$//; s/_/-/g'); \
		echo "Building $$img_name from mcp_servers/$$server ..."; \
		$(CONTAINER_RUNTIME) build -t $(MCP_IMAGE_REGISTRY)/$$img_name:$(MCP_IMAGE_TAG) \
			-f ../../mcp_servers/$$server/Containerfile ../../mcp_servers/$$server; \
	done

push-mcp-images: build-mcp-images ## Build and push MCP server images to registry
	@for server in $(MCP_SERVERS); do \
		img_name=$$(echo "mcp-$$server" | sed 's/_mcp$$//; s/_/-/g'); \
		echo "Pushing $(MCP_IMAGE_REGISTRY)/$$img_name:$(MCP_IMAGE_TAG) ..."; \
		$(CONTAINER_RUNTIME) push $(MCP_IMAGE_REGISTRY)/$$img_name:$(MCP_IMAGE_TAG); \
	done

install-status: ## Check deployment status
	@echo "Deployment status for namespace: $(NAMESPACE)"
	@echo "============================================"
	@echo ""
	@echo "Pods:"
	@oc get pods -n $(NAMESPACE) || true
	@echo ""
	@echo "Services:"
	@oc get svc -n $(NAMESPACE) || true
	@echo ""
	@echo "Routes:"
	@oc get routes -n $(NAMESPACE) || true
	@echo ""
	@echo "Secrets:"
	@oc get secrets -n $(NAMESPACE) | grep huggingface-secret || true
	@echo ""
	@echo "PVCs:"
	@oc get pvc -n $(NAMESPACE) || true
