# AI Virtual Agent - Helm Deployment Makefile
# Run `make help` to see available targets.

.PHONY: help install install-help install-status deps uninstall install-namespace list-models

# -----------------------------------------------------------------------------
# Helper
# -----------------------------------------------------------------------------
help: ## Show help for helm deployment targets
	@echo "AI Virtual Agent - Helm Deployment Commands"
	@echo "==========================================="
	@echo ""
	@echo "☸️  Deployment Commands:"
	@grep -E '^(install|install-help|install-status|deps|uninstall|list-models):.*?## ' $(MAKEFILE_LIST) | \
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

# Helm argument builders
helm_pgvector_args = \
    --set pgvector.secret.user=$(POSTGRES_USER) \
    --set pgvector.secret.password=$(POSTGRES_PASSWORD) \
    --set pgvector.secret.dbname=$(POSTGRES_DBNAME)

helm_minio_args = \
    --set minio.secret.user=$(MINIO_USER) \
    --set minio.secret.password=$(MINIO_PASSWORD)

helm_llm_service_args = \
    --set llm-service.secret.hf_token=$(HF_TOKEN) \
    $(if $(LLM),--set global.models.$(LLM).enabled=true,) \
    $(if $(SAFETY),--set global.models.$(SAFETY).enabled=true,) \
    $(if $(LLM_TOLERATION),--set-json global.models.$(LLM).tolerations='$(call TOLERATIONS_TEMPLATE,$(LLM_TOLERATION))',) \
    $(if $(SAFETY_TOLERATION),--set-json global.models.$(SAFETY).tolerations='$(call TOLERATIONS_TEMPLATE,$(SAFETY_TOLERATION))',)

helm_llama_stack_args = \
    $(if $(LLM),--set global.models.$(LLM).enabled=true,) \
    $(if $(SAFETY),--set global.models.$(SAFETY).enabled=true,) \
    $(if $(LLM_URL),--set global.models.$(LLM).url='$(LLM_URL)',) \
    $(if $(SAFETY_URL),--set global.models.$(SAFETY).url='$(SAFETY_URL)',) \
    $(if $(LLM_API_TOKEN),--set global.models.$(LLM).apiToken='$(LLM_API_TOKEN)',) \
    $(if $(SAFETY_API_TOKEN),--set global.models.$(SAFETY).apiToken='$(SAFETY_API_TOKEN)',) \
    $(if $(TAVILY_API_KEY),--set llama-stack.secrets.TAVILY_SEARCH_API_KEY='$(TAVILY_API_KEY)',) \
    $(if $(LLAMA_STACK_ENV),--set-json llama-stack.secrets='$(LLAMA_STACK_ENV)',)

helm_ingestion_args = \
	--set configure-pipeline.notebook.create=false \
	--set ingestion-pipeline.defaultPipeline.enabled=false \
	--set ingestion-pipeline.authUser=$(AUTH_INGESTION_PIPELINE_USER)

helm_seed_admin_user_args = \
    $(if $(ADMIN_USERNAME),--set seed.admin_user.username='$(ADMIN_USERNAME)',) \
    $(if $(ADMIN_EMAIL),--set seed.admin_user.email='$(ADMIN_EMAIL)',)

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
	@echo "  ADMIN_USERNAME           - Admin user name"
	@echo "  ADMIN_EMAIL              - Admin user email"
	@echo "  {SAFETY,LLM}             - Model id as defined in values (eg. llama-3-2-1b-instruct)"
	@echo "  {SAFETY,LLM}_URL         - Model URL"
	@echo "  {SAFETY,LLM}_API_TOKEN   - Model API token for remote models"
	@echo "  {SAFETY,LLM}_TOLERATION  - Model pod toleration"
	@echo ""
	@echo "Example usage:"
	@echo "  make install NAMESPACE=my-ai-assistant"
	@echo "  make install-status NAMESPACE=my-ai-assistant"

deps: ## Update Helm dependencies
	@echo "Updating Helm dependencies"
	#@helm dependency update $(AI_VIRTUAL_AGENT_CHART) &> /dev/null

list-models: deps ## List available models
	@helm template dummy-release $(AI_VIRTUAL_AGENT_CHART) --set llm-service._debugListModels=true | grep ^model:

install-namespace: ## Create and configure deployment namespace
	@oc create namespace $(NAMESPACE) &> /dev/null && oc label namespace $(NAMESPACE) modelmesh-enabled=false ||:
	@oc project $(NAMESPACE) &> /dev/null ||:

install: install-namespace deps ## Install the AI Virtual Agent deployment
	@./scripts/install_with_env.sh $(NAMESPACE) $(AI_VIRTUAL_AGENT_RELEASE) $(AI_VIRTUAL_AGENT_CHART)

	@echo "Waiting for model services and llamastack to deploy. It may take around 10-15 minutes depending on the size of the model..."
	@oc rollout status deploy/ai-virtual-agent -n $(NAMESPACE)
	@echo "$(AI_VIRTUAL_AGENT_RELEASE) installed successfully"
	@echo ""
	@echo "Getting application URL..."
	@sleep 5
	@$(eval APP_URL := $(shell oc get routes ai-virtual-agent-authenticated -n $(NAMESPACE) -o jsonpath='{.status.ingress[0].host}' 2>/dev/null || echo ""))
	@if [ -n "$(APP_URL)" ]; then \
		echo "🎉 Application is ready!"; \
		echo "📱 Access your AI Virtual Agent at: https://$(APP_URL)"; \
	else \
		echo "⚠️  Route not ready yet. Get the URL manually with:"; \
		echo "   oc get routes ai-virtual-agent-authenticated -n $(NAMESPACE)"; \
	fi
	@echo ""

uninstall: ## Uninstall deployment and clean up resources
	@echo "Uninstalling $(AI_VIRTUAL_AGENT_RELEASE) helm chart from namespace $(NAMESPACE)"
	@helm uninstall --ignore-not-found $(AI_VIRTUAL_AGENT_RELEASE) -n $(NAMESPACE)
	@echo "Removing pgvector and minio PVCs from $(NAMESPACE)"
	@oc get pvc -n $(NAMESPACE) -o custom-columns=NAME:.metadata.name | grep -E '^(pg|minio)-data' | xargs -I {} oc delete pvc -n $(NAMESPACE) {} ||:
	@echo "Deleting remaining pods in namespace $(NAMESPACE)"
	@oc delete pods -n $(NAMESPACE) --all
	@echo "Checking for any remaining resources in namespace $(NAMESPACE)..."
	@echo "If you want to completely remove the namespace, run: oc delete project $(NAMESPACE)"
	@echo "Remaining resources in namespace $(NAMESPACE):"
	@$(MAKE) install-status NAMESPACE=$(NAMESPACE)

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
