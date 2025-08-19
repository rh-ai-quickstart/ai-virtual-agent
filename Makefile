# AI Virtual Agent Quickstart – Top-level Makefile
# This makefile routes targets to local or helm specific makefiles

.PHONY: all local helm help

<<<<<<< HEAD
all: ## Show usage instructions
	@echo "AI Virtual Agent Quickstart"
	@echo "========================="
=======
# -----------------------------------------------------------------------------
# Global environment loading
# -----------------------------------------------------------------------------

# Use bash for better shell compatibility
SHELL := /bin/bash

# If a .env file exists in the project root, load it and export variables
ifneq (,$(wildcard .env))
include .env
endif

# Export all variables to recipe environments
.EXPORT_ALL_VARIABLES:

# -----------------------------------------------------------------------------
# Helper
# -----------------------------------------------------------------------------
help: ## Show comprehensive help for all available targets
	@echo "AI Virtual Agent Kickstart - Available Make Targets"
	@echo "==================================================="
>>>>>>> 146fd5c (style: apply pre-commit fixes; tests/docs/attachments improvements)
	@echo ""
	@echo "Usage:"
	@echo "  make local/<target>   - Run local development targets"
	@echo "  make helm/<target>    - Run helm deployment targets"
	@echo ""
	@echo "Examples:"
	@echo "  make local/dev        - Start local development environment"
	@echo "  make local/help       - Show local development help"
	@echo "  make helm/install     - Install via helm (requires NAMESPACE)"
	@echo "  make helm/help        - Show helm deployment help"
	@echo ""
	@echo "For target-specific help:"
	@echo "  make local/help"
	@echo "  make helm/help"

help: all ## Show help (alias for all)

local/%: ## Route local targets to deploy/local/Makefile
	$(MAKE) -C deploy/local $*

helm/%: ## Route helm targets to deploy/helm/Makefile
	$(MAKE) -C deploy/helm $*
