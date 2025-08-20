# AI Virtual Agent Quickstart – Top-level Makefile
# This makefile routes targets to local or helm specific makefiles

.PHONY: all local helm help

SHELL := /bin/bash

ifneq (,$(wildcard .env))
include .env
endif

.EXPORT_ALL_VARIABLES:

all: ## Show usage instructions
	@echo "AI Virtual Agent Quickstart"
	@echo "========================="
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
