"""
Agent Templates API endpoints for managing predefined agent templates.

This module provides endpoints for initializing agents from predefined templates,
including automatic knowledge base creation and data ingestion for various use cases.

Key Features:
- Predefined agent templates with specialized roles across multiple categories
- Automatic knowledge base creation with domain-specific data
- Template customization options (custom names, prompts)
- Bulk initialization of all templates or specific suites
- Integration with existing agent and knowledge base APIs
"""

import os
from typing import Dict, List, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from .. import schemas
from ..routes.knowledge_bases import create_knowledge_base
from ..routes.virtual_assistants import create_virtual_assistant
from ..utils.logging_config import get_logger
from ..utils.template_loader import load_all_templates_from_directory, get_suites_by_category as get_suites_by_category_util

from ..database import AsyncSessionLocal
from .. import models
from sqlalchemy import select
import asyncio

logger = get_logger(__name__)

router = APIRouter(prefix="/agent_templates", tags=["agent_templates"])


class AgentTemplate(BaseModel):
    """Schema for agent template configuration."""
    name: str
    persona: str
    prompt: str
    model_name: str
    tools: List[Dict[str, str]]
    knowledge_base_ids: List[str]
    knowledge_base_config: Optional[Dict] = None


class TemplateInitializationRequest(BaseModel):
    """Schema for template initialization request."""
    template_name: str
    custom_name: Optional[str] = None
    custom_prompt: Optional[str] = None
    include_knowledge_base: bool = True


class TemplateInitializationResponse(BaseModel):
    """Schema for template initialization response."""
    agent_id: str
    agent_name: str
    persona: str
    knowledge_base_created: bool
    knowledge_base_name: Optional[str] = None
    status: str
    message: str

# Load templates from YAML files
try:
    ALL_SUITES, ALL_AGENT_TEMPLATES = load_all_templates_from_directory()
    logger.info(f"Successfully loaded {len(ALL_SUITES)} suites and {len(ALL_AGENT_TEMPLATES)} templates from YAML")
except Exception as e:
    logger.error(f"Failed to load templates from YAML: {e}")
    # Fallback to empty templates to prevent crashes
    ALL_SUITES = {}
    ALL_AGENT_TEMPLATES = {}

# All templates for general access (loaded from YAML)
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
    Get detailed information about all categories including names, descriptions, and icons.
    
    Returns:
        Dictionary with category information
    """
    categories_info = {}
    
    for suite_id, suite_config in ALL_SUITES.items():
        category = suite_config["category"]
        if category not in categories_info:
            categories_info[category] = {
                "name": f"{category.replace('_', ' ').title()} Templates",
                "description": f"Specialized agents for {category.replace('_', ' ')} services.",
                "icon": category,
                "suite_count": 0
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
            detail=f"Suite '{suite_name}' not found. Available suites: {list(ALL_SUITES.keys())}"
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
        "agent_names": agent_names
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
            detail=f"Template '{template_name}' not found. Available templates: {list(ALL_AGENT_TEMPLATES.keys())}"
        )
    
    return ALL_AGENT_TEMPLATES[template_name]

@router.post("/initialize", response_model=TemplateInitializationResponse)
async def initialize_agent_from_template(request: TemplateInitializationRequest, http_request: Request):
    """
    Initialize an agent from a template with optional knowledge base creation.
    
    This endpoint creates an agent based on a predefined template and optionally
    creates and ingests data into a knowledge base for RAG functionality.
    
    Args:
        request: Template initialization request with customization options
        
    Returns:
        TemplateInitializationResponse: Details about the created agent and knowledge base
        
    Raises:
        HTTPException: If template not found or initialization fails
    """
    if request.template_name not in ALL_AGENT_TEMPLATES:
        raise HTTPException(
            status_code=404,
            detail=f"Template '{request.template_name}' not found. Available templates: {list(ALL_AGENT_TEMPLATES.keys())}"
        )
    
    template = ALL_AGENT_TEMPLATES[request.template_name]
    
    try:
        # Step 1: Create knowledge base if requested
        knowledge_base_created = False
        knowledge_base_name = None
        
        if request.include_knowledge_base and template.knowledge_base_config:
            try:
                kb_config = template.knowledge_base_config.copy()
                
                
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(models.KnowledgeBase).where(
                            models.KnowledgeBase.vector_db_name == kb_config["vector_db_name"]
                        )
                    )
                    existing_kb = result.scalar_one_or_none()
                    
                    if existing_kb:
                        logger.info(f"Knowledge base '{kb_config['vector_db_name']}' already exists, skipping creation")
                        knowledge_base_created = True
                        knowledge_base_name = existing_kb.name
                    else:
                        # Create knowledge base
                        kb_create = schemas.KnowledgeBaseCreate(**kb_config)
                        created_kb = await create_knowledge_base(kb_create, db)
                        knowledge_base_created = True
                        knowledge_base_name = created_kb.name
                        logger.info(f"Successfully created knowledge base: {created_kb.name}")
                        
            except Exception as kb_error:
                logger.warning(f"Failed to create knowledge base for template {request.template_name}: {str(kb_error)}")
                # Continue without knowledge base
        
        # Step 2: Create agent
        agent_name = request.custom_name or template.name
        agent_prompt = request.custom_prompt or template.prompt
        
        # Convert template tools to schema format
        tools = [schemas.ToolAssociationInfo(**tool) for tool in template.tools]
        
        # Add RAG tool if knowledge base was created
        if knowledge_base_created and template.knowledge_base_ids:
            tools.append(schemas.ToolAssociationInfo(toolgroup_id="builtin::rag"))
        
        agent_config = schemas.VirtualAssistantCreate(
            name=agent_name,
            prompt=agent_prompt,
            model_name=template.model_name,
            tools=tools,
            knowledge_base_ids=template.knowledge_base_ids if knowledge_base_created else [],
            temperature=0.1,
            top_p=0.95,
            max_tokens=4096,
            repetition_penalty=1.0,
            max_infer_iters=10,
            input_shields=[],
            output_shields=[],
            enable_session_persistence=False
        )
        
        created_agent = await create_virtual_assistant(agent_config, http_request)
        
        logger.info(f"Successfully created agent '{agent_name}' from template '{request.template_name}'")
        
        return TemplateInitializationResponse(
            agent_id=created_agent.id,
            agent_name=created_agent.name,
            persona=template.persona,
            knowledge_base_created=knowledge_base_created,
            knowledge_base_name=knowledge_base_name,
            status="success",
            message=f"Agent '{agent_name}' initialized successfully from template '{request.template_name}'"
        )
        
    except Exception as e:
        logger.error(f"Failed to initialize agent from template '{request.template_name}': {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize agent from template: {str(e)}"
        )

@router.post("/initialize-suite/{suite_name}", response_model=List[TemplateInitializationResponse])
async def initialize_suite(suite_name: str, http_request: Request):
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
            detail=f"Suite '{suite_name}' not found. Available suites: {list(ALL_SUITES.keys())}"
        )
    
    suite = ALL_SUITES[suite_name]
    results = []
    
    for template_name in suite["templates"].keys():
        try:
            request = TemplateInitializationRequest(
                template_name=template_name,
                include_knowledge_base=True
            )
            
            result = await initialize_agent_from_template(request, http_request)
            results.append(result)
            
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Failed to initialize template '{template_name}' in suite '{suite_name}': {str(e)}")
            results.append(TemplateInitializationResponse(
                agent_id="",
                agent_name=template_name,
                persona=suite["templates"][template_name].persona,
                knowledge_base_created=False,
                knowledge_base_name=None,
                status="error",
                message=f"Failed to initialize template '{template_name}': {str(e)}"
            ))
    
    return results

@router.post("/initialize-all", response_model=List[TemplateInitializationResponse])
async def initialize_all_templates(http_request: Request):
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
                template_name=template_name,
                include_knowledge_base=True
            )
            
            result = await initialize_agent_from_template(request, http_request)
            results.append(result)
            
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Failed to initialize template '{template_name}': {str(e)}")
            results.append(TemplateInitializationResponse(
                agent_id="",
                agent_name=template_name,
                persona=ALL_AGENT_TEMPLATES[template_name].persona,
                knowledge_base_created=False,
                knowledge_base_name=None,
                status="error",
                message=f"Failed to initialize template '{template_name}': {str(e)}"
            ))
    
    return results 