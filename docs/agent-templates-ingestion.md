# Agent Templates Ingestion Capability

## Overview

The agent templates ingestion capability allows users to initialize pre-configured agents from templates across multiple categories, with automatic knowledge base creation and data ingestion. This feature provides a comprehensive agent initialization experience supporting banking, travel & hospitality, wealth management, and other specialized domains.

## Architecture

### Backend Components

#### 1. Agent Templates API (`backend/routes/agent_templates.py`)

The agent templates API provides the following endpoints:

- `GET /api/agent_templates/` - Get list of available templates
- `GET /api/agent_templates/suites` - Get list of available suites
- `GET /api/agent_templates/suites/categories` - Get suites grouped by category
- `GET /api/agent_templates/categories/info` - Get detailed category information
- `GET /api/agent_templates/suites/{suite_name}/details` - Get suite details
- `GET /api/agent_templates/{template_name}` - Get detailed template information
- `POST /api/agent_templates/initialize` - Initialize a single agent from template
- `POST /api/agent_templates/initialize-suite/{suite_name}` - Initialize all agents in a suite
- `POST /api/agent_templates/initialize-all` - Initialize all templates at once

#### 2. Template Configuration System

Templates are now configured using YAML files in the `backend/agent_templates/` directory:

- **Suite-based Organization**: Templates are organized into suites by category
- **YAML Configuration**: Each suite is defined in a separate YAML file
- **Dynamic Loading**: Templates are loaded at startup from YAML files
- **Category Support**: Multiple categories (banking, travel, etc.)

#### 3. Template Loader (`backend/utils/template_loader.py`)

The template loader utility provides:

- YAML file parsing and validation
- Template conversion to internal format
- Suite and category organization
- Error handling for malformed templates

### Available Template Categories

The system now supports multiple categories with specialized agent templates:

#### 1. Banking Category

**Business Banking Suite** (`business_banking.yaml`):
- **Commercial Banking Specialist** (`commercial_banker`)
  - Focus: Commercial lending, cash management, trade finance
  - Knowledge Base: `commercial_banking_kb`

- **Business Advisory Specialist** (`business_advisor`)
  - Focus: Strategic guidance, business planning, growth strategies
  - Knowledge Base: `business_advisory_kb`

**Core Banking Suite** (`core_banking.yaml`):
- **Compliance Officer** (`compliance_officer`)
  - Focus: Banking regulations, BSA/AML, OFAC compliance
  - Knowledge Base: `compliance_kb`

- **Relationship Manager** (`relationship_manager`)
  - Focus: Lending policies, credit assessment, loan procedures
  - Knowledge Base: `lending_kb`

- **Branch Teller** (`branch_teller`)
  - Focus: Customer service, account policies, transaction processing
  - Knowledge Base: `customer_service_kb`

- **Fraud Analyst** (`fraud_analyst`)
  - Focus: Fraud detection, AML/BSA alerts, suspicious activity
  - Knowledge Base: `fraud_kb`

#### 2. Travel & Hospitality Category

**Travel & Hospitality Suite** (`travel_hospitality.yaml`):
- **Travel Agent Specialist** (`travel_agent`)
  - Focus: Travel planning, bookings, destination advice
  - Knowledge Base: `travel_agent_kb`

- **Hotel Concierge Assistant** (`hotel_concierge`)
  - Focus: Guest services, reservations, local recommendations
  - Knowledge Base: `hotel_concierge_kb`

- **Tour Guide Assistant** (`tour_guide`)
  - Focus: Historical facts, cultural insights, destination information
  - Knowledge Base: `tour_guide_kb`

#### 3. Wealth Management Category

**Wealth Management Suite** (`wealth_management.yaml`):
- **Investment Advisor** (`investment_advisor`)
  - Focus: Investment strategies, portfolio management, market analysis
  - Knowledge Base: `investment_advisor_kb`

- **Financial Planner** (`financial_planner`)
  - Focus: Financial planning, retirement strategies, tax optimization
  - Knowledge Base: `financial_planner_kb`

## Data Ingestion Process

### 1. Knowledge Base Creation

When a template is initialized:

1. **Template Validation**: Verify template exists and configuration is valid
2. **Knowledge Base Check**: Check if knowledge base already exists
3. **Knowledge Base Creation**: Create new knowledge base if needed
4. **Data Ingestion**: Automatically ingest domain-specific data

### 2. Agent Creation

After knowledge base setup:

1. **Agent Configuration**: Build agent config from template
2. **Tool Assignment**: Assign appropriate tools (websearch, RAG if knowledge base exists)
3. **Agent Creation**: Create agent via LlamaStack API