"""
Agent Templates API endpoints for managing predefined agent templates.

This module provides endpoints for initializing agents from predefined
templates, including automatic knowledge base creation and data ingestion
for various use cases.

Key Features:
- Predefined agent templates with specialized roles across multiple categories
- Automatic knowledge base creation with domain-specific data
- Template customization options (custom names, prompts)
- Bulk initialization of all templates or specific suites
- Integration with existing agent and knowledge base APIs
"""

import asyncio
import logging
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.template_loader import (
    get_suites_by_category as get_suites_by_category_util,
)
from ...core.template_loader import (
    load_all_templates_from_directory,
)
from ...crud.knowledge_bases import knowledge_bases
from ...crud.virtual_agents import virtual_agents
from ...database import get_db
from ...schemas import (
    AgentTemplate,
    KnowledgeBaseCreate,
    TemplateInitializationRequest,
    TemplateInitializationResponse,
    ToolAssociationInfo,
    VirtualAgentCreate,
)
from .knowledge_bases import create_knowledge_base_internal
from .virtual_agents import create_virtual_agent_internal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent_templates", tags=["agent_templates"])


# Load templates from YAML files
try:
    ALL_SUITES, ALL_AGENT_TEMPLATES = load_all_templates_from_directory()
    logger.info(
        f"Successfully loaded {len(ALL_SUITES)} suites and "
        f"{len(ALL_AGENT_TEMPLATES)} templates from YAML"
    )
except Exception as e:
    logger.error(f"Failed to load templates from YAML: {e}")
    # Fallback to empty templates to prevent crashes
    ALL_SUITES = {}
    ALL_AGENT_TEMPLATES = {}


@router.get("/", response_model=List[str])
async def get_available_templates():
    """
    Get list of available agent templates.

    Returns:
        List of template names that can be used for agent initialization
    """
    logger.info(f"Available templates: {list(ALL_AGENT_TEMPLATES.keys())}")
    logger.info(f"Total templates loaded: {len(ALL_AGENT_TEMPLATES)}")
    return list(ALL_AGENT_TEMPLATES.keys())


@router.get("/suites", response_model=List[str])
async def get_available_suites():
    """
    Get list of available suites.

    Returns:
        List of suite names that can be used for bulk initialization
    """
    return list(ALL_SUITES.keys())


@router.get("/suites/categories", response_model=Dict[str, List[str]])
async def get_suites_by_category():
    """
    Get suites grouped by category.

    Returns:
        Dictionary with categories as keys and lists of suite names as values
    """
    result = get_suites_by_category_util(ALL_SUITES)
    logger.info(f"Suites by category: {result}")
    logger.info(f"Total suites loaded: {len(ALL_SUITES)}")
    return result


@router.get("/categories/info")
async def get_categories_info():
    """
    Get detailed information about all categories including names,
    descriptions, and icons.

    Returns:
        Dictionary with category information
    """
    categories_info = {}

    for suite_id, suite_config in ALL_SUITES.items():
        category = suite_config["category"]
        if category not in categories_info:
            categories_info[category] = {
                "name": f"{category.replace('_', ' ').title()} Templates",
                "description": f"Specialized agents for "
                f"{category.replace('_', ' ')} services.",
                "icon": category,
                "suite_count": 0,
            }
        categories_info[category]["suite_count"] += 1

    logger.info(f"Categories info: {categories_info}")
    return categories_info


@router.get("/suites/{suite_name}/details")
async def get_suite_details(suite_name: str):
    """
    Get detailed information about a specific suite including agent names.
    """
    if suite_name not in ALL_SUITES:
        raise HTTPException(
            status_code=404,
            detail=f"Suite '{suite_name}' not found. "
            f"Available suites: {list(ALL_SUITES.keys())}",
        )

    suite = ALL_SUITES[suite_name]
    templates = suite["templates"]

    # Extract agent names from templates
    agent_names = [template.name for template in templates.values()]

    return {
        "id": suite_name,
        "name": suite["name"],
        "description": suite["description"],
        "category": suite["category"],
        "agent_count": len(templates),
        "agent_names": agent_names,
        # Also include the underlying template IDs so the UI can deploy a subset
        # of agents from the suite by calling the single-template initialize API.
        "template_ids": list(templates.keys()),
    }


@router.get("/{template_name}", response_model=AgentTemplate)
async def get_template_details(template_name: str):
    """
    Get detailed information about a specific template.

    Args:
        template_name: Name of the template to retrieve

    Returns:
        AgentTemplate: Template configuration details

    Raises:
        HTTPException: If template not found
    """
    if template_name not in ALL_AGENT_TEMPLATES:
        raise HTTPException(
            status_code=404,
            detail=f"Template '{template_name}' not found. "
            f"Available templates: {list(ALL_AGENT_TEMPLATES.keys())}",
        )

    return ALL_AGENT_TEMPLATES[template_name]


@router.post("/initialize", response_model=TemplateInitializationResponse)
async def initialize_agent_from_template(
    request: TemplateInitializationRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Initialize an agent from a template with optional knowledge base creation.

    This endpoint creates an agent based on a predefined template and
    optionally creates and ingests data into a knowledge base for
    RAG functionality.

    Args:
        request: Template initialization request with customization options

    Returns:
        TemplateInitializationResponse: Details about the created agent and
            knowledge base

    Raises:
        HTTPException: If template not found or initialization fails
    """
    if request.template_name not in ALL_AGENT_TEMPLATES:
        raise HTTPException(
            status_code=404,
            detail=f"Template '{request.template_name}' not found. "
            f"Available templates: {list(ALL_AGENT_TEMPLATES.keys())}",
        )

    template = ALL_AGENT_TEMPLATES[request.template_name]

    try:
        # Compute target agent name early for messages and duplicate checks
        agent_name = request.custom_name or template.name

        # Duplicate check: simple, early return by template_id
        existing_agent = await virtual_agents.get_by_template_id(
            db, template_id=request.template_name
        )
        if existing_agent:
            logger.info(
                f"Agent already deployed for template "
                f"{request.template_name}: {existing_agent.id}"
            )
            return TemplateInitializationResponse(
                agent_id="",
                agent_name=agent_name,
                persona=template.persona,
                knowledge_base_created=False,
                knowledge_base_name=None,
                status="skipped",
                message=(
                    f"Agent '{agent_name}' is already deployed. "
                    f"Check your 'My Agents' page."
                ),
            )

        # Step 1: Create knowledge base if requested
        knowledge_base_created = False
        knowledge_base_name = None

        if request.include_knowledge_base and template.knowledge_base_config:
            try:
                kb_config = template.knowledge_base_config.copy()

                existing_kb = await knowledge_bases.get_by_vector_store_name(
                    db, vector_store_name=kb_config["vector_store_name"]
                )

                if existing_kb:
                    logger.info(
                        f"Knowledge base '{kb_config['vector_store_name']}' "
                        f"already exists, skipping creation"
                    )
                    knowledge_base_created = True
                    knowledge_base_name = existing_kb.name
                else:
                    # Create knowledge base
                    kb_create = KnowledgeBaseCreate(**kb_config)
                    created_kb = await create_knowledge_base_internal(kb_create, db)
                    knowledge_base_created = True
                    knowledge_base_name = created_kb.name
                    logger.info(
                        f"Successfully created knowledge base: " f"{created_kb.name}"
                    )

            except Exception as kb_error:
                logger.warning(
                    f"Failed to create knowledge base for template "
                    f"{request.template_name}: {str(kb_error)}"
                )
                # Continue without knowledge base

        # Step 2: Create agent
        agent_prompt = request.custom_prompt or template.prompt

        # Determine tools: prefer overrides if provided, otherwise template tools
        if request.tools is not None:
            tools = list(request.tools)
        else:
            tools = [ToolAssociationInfo(**tool) for tool in template.tools]

        # Add RAG tool if knowledge base was created
        if knowledge_base_created and template.knowledge_base_ids:
            tools.append(ToolAssociationInfo(toolgroup_id="builtin::rag"))

        # Determine model: prefer override if provided and non-empty
        model_to_use = request.model_name or template.model_name

        agent_config = VirtualAgentCreate(
            name=agent_name,
            prompt=agent_prompt,
            model_name=model_to_use,
            tools=tools,
            knowledge_base_ids=(
                template.knowledge_base_ids if knowledge_base_created else []
            ),
            temperature=0.1,
            top_p=0.95,
            max_tokens=4096,
            repetition_penalty=1.0,
            max_infer_iters=10,
            input_shields=[],
            output_shields=[],
            enable_session_persistence=False,
        )

        # Include template_id in the agent config
        agent_config.template_id = request.template_name

        created_agent = await create_virtual_agent_internal(
            agent_config, http_request, db
        )

        logger.info(
            f"Successfully created agent '{agent_name}' from template "
            f"'{request.template_name}'"
        )
        return TemplateInitializationResponse(
            agent_id=created_agent.id,
            agent_name=created_agent.name,
            persona=template.persona,
            knowledge_base_created=knowledge_base_created,
            knowledge_base_name=knowledge_base_name,
            status="success",
            message=f"Agent '{agent_name}' initialized successfully "
            f"from template '{request.template_name}'",
        )

    except Exception as e:
        logger.error(
            f"Failed to initialize agent from template "
            f"'{request.template_name}': {str(e)}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize agent from template: {str(e)}",
        )


@router.post(
    "/initialize-suite/{suite_name}",
    response_model=List[TemplateInitializationResponse],
)
async def initialize_suite(
    suite_name: str, http_request: Request, db: AsyncSession = Depends(get_db)
):
    """
    Initialize all agents from a specific suite.

    This endpoint creates all agents within a suite with their respective
    knowledge bases. This is useful for setting up a complete suite.

    Args:
        suite_name: Name of the suite to initialize

    Returns:
        List[TemplateInitializationResponse]: Details about all created agents

    Raises:
        HTTPException: If suite not found or initialization fails
    """
    if suite_name not in ALL_SUITES:
        raise HTTPException(
            status_code=404,
            detail=f"Suite '{suite_name}' not found. "
            f"Available suites: {list(ALL_SUITES.keys())}",
        )

    suite = ALL_SUITES[suite_name]
    results = []

    for template_name in suite["templates"].keys():
        try:
            request = TemplateInitializationRequest(
                template_name=template_name, include_knowledge_base=True
            )

            result = await initialize_agent_from_template(request, http_request, db)
            results.append(result)

            await asyncio.sleep(1)

        except Exception as e:
            logger.error(
                f"Failed to initialize template '{template_name}' "
                f"in suite '{suite_name}': {str(e)}"
            )
            results.append(
                TemplateInitializationResponse(
                    agent_id="",
                    agent_name=template_name,
                    persona=suite["templates"][template_name].persona,
                    knowledge_base_created=False,
                    knowledge_base_name=None,
                    status="error",
                    message=f"Failed to initialize template "
                    f"'{template_name}': {str(e)}",
                )
            )

    return results


@router.post("/initialize-all", response_model=List[TemplateInitializationResponse])
async def initialize_all_templates(
    http_request: Request, db: AsyncSession = Depends(get_db)
):
    """
    Initialize all agent templates at once.

    This endpoint creates all available agent templates with their respective
    knowledge bases. This is useful for setting up a complete agent
    environment with all available templates.

    Returns:
        List[TemplateInitializationResponse]: Details about all created agents

    Raises:
        HTTPException: If initialization fails
    """
    results = []

    for template_name in ALL_AGENT_TEMPLATES.keys():
        try:
            request = TemplateInitializationRequest(
                template_name=template_name, include_knowledge_base=True
            )

            result = await initialize_agent_from_template(request, http_request, db)
            results.append(result)

            await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Failed to initialize template '{template_name}': {str(e)}")
            results.append(
                TemplateInitializationResponse(
                    agent_id="",
                    agent_name=template_name,
                    persona=ALL_AGENT_TEMPLATES[template_name].persona,
                    knowledge_base_created=False,
                    knowledge_base_name=None,
                    status="error",
                    message=f"Failed to initialize template "
                    f"'{template_name}': {str(e)}",
                )
            )

    return results
