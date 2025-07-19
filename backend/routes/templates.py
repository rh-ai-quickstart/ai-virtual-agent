"""
Template API endpoints for managing AI agent templates.

This module provides endpoints for loading, retrieving, and deploying
YAML-based agent templates. Templates define pre-configured agent suites
for different business domains and use cases.

Key Features:
- Load and retrieve agent templates from YAML files
- Deploy multiple agents from a single template
- Template validation and error handling
- Bulk agent creation with progress tracking
- Integration with existing virtual_assistants patterns
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from llama_stack_client.lib.agents.agent import AgentUtils

from .. import schemas
from ..api.llamastack import client
from ..services.template_service import template_service
from ..utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/templates", tags=["templates"])


def get_strategy(temperature, top_p):
    """
    Determines the sampling strategy for the LLM based on temperature.
    Reused from virtual_assistants.py for consistency.
    """
    return (
        {"type": "greedy"}
        if temperature == 0
        else {"type": "top_p", "temperature": temperature, "top_p": top_p}
    )


@router.get("/", response_model=List[schemas.TemplateSuiteRead])
async def get_templates():
    """
    Retrieve all available agent templates.
    
    Returns:
        List of all template suites with their agent configurations
        
    Raises:
        HTTPException: If template loading fails
    """
    try:
        logger.info("=== DEBUG: get_templates() called ===")
        logger.info("=== DEBUG: About to call template_service.load_templates() ===")
        templates = template_service.load_templates()
        logger.info(f"Retrieved {len(templates)} templates")
        logger.info(f"=== DEBUG: Returning {len(templates)} templates ===")
        return templates
    except Exception as e:
        logger.error(f"Failed to load templates: {str(e)}")
        logger.error(f"=== DEBUG: Exception in get_templates: {str(e)} ===")
        import traceback
        logger.error(f"=== DEBUG: Full traceback: {traceback.format_exc()} ===")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load templates: {str(e)}"
        )


@router.get("/debug", response_model=Dict[str, Any])
async def debug_templates():
    """Debug endpoint to check template loading"""
    try:
        logger.info("=== DEBUG: debug_templates() called ===")
        
        # Check if templates directory exists
        templates_dir = template_service.templates_dir
        logger.info(f"Templates directory: {templates_dir}")
        logger.info(f"Templates directory exists: {templates_dir.exists()}")
        logger.info(f"Templates directory absolute path: {templates_dir.absolute()}")
        
        # List all YAML files
        yaml_files = list(templates_dir.glob("*.yaml"))
        logger.info(f"Found {len(yaml_files)} YAML files: {[f.name for f in yaml_files]}")
        
        # Try to load each file individually to see what's failing
        detailed_results = []
        for yaml_file in yaml_files:
            try:
                logger.info(f"=== Trying to load {yaml_file} ===")
                template_data = template_service._load_yaml_file(yaml_file)
                logger.info(f"Successfully loaded YAML data from {yaml_file}")
                
                # Try validation
                is_valid, validation_errors = template_service._validate_template_structure(template_data, yaml_file)
                logger.info(f"Validation result for {yaml_file}: valid={is_valid}, errors={validation_errors}")
                
                if is_valid:
                    # Try conversion
                    template_schema = template_service._convert_to_schema(template_data)
                    logger.info(f"Successfully converted {yaml_file} to schema")
                    detailed_results.append({
                        "file": yaml_file.name,
                        "status": "success",
                        "template_id": template_schema.id,
                        "template_name": template_schema.name
                    })
                else:
                    detailed_results.append({
                        "file": yaml_file.name,
                        "status": "validation_failed",
                        "errors": validation_errors
                    })
                    
            except Exception as e:
                logger.error(f"Failed to process {yaml_file}: {str(e)}")
                detailed_results.append({
                    "file": yaml_file.name,
                    "status": "error",
                    "error": str(e)
                })
        
        # Try to load templates normally
        templates = template_service.load_templates(force_reload=True)
        logger.info(f"Successfully loaded {len(templates)} templates")
        
        return {
            "message": "Templates route is working",
            "template_count": len(templates),
            "templates_dir": str(templates_dir),
            "templates_dir_absolute": str(templates_dir.absolute()),
            "templates_dir_exists": templates_dir.exists(),
            "yaml_files": [f.name for f in yaml_files],
            "detailed_results": detailed_results,
            "templates": [{"id": t.id, "name": t.name, "category": t.category} for t in templates]
        }
    except Exception as e:
        logger.error(f"=== DEBUG: Exception in debug_templates: {str(e)} ===")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "message": "Error in templates route",
            "error": str(e),
            "templates_dir": str(template_service.templates_dir),
            "templates_dir_absolute": str(template_service.templates_dir.absolute()),
            "templates_dir_exists": template_service.templates_dir.exists()
        }


@router.get("/categories", response_model=List[str])
async def get_template_categories():
    """
    Get all available template categories.
    
    Returns:
        List of template categories (e.g., ["fsi_banking", "us_banking"])
        
    Raises:
        HTTPException: If template loading fails
    """
    try:
        categories = template_service.get_categories()
        logger.info(f"Retrieved {len(categories)} template categories")
        return categories
    except Exception as e:
        logger.error(f"Failed to get template categories: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get template categories: {str(e)}"
        )


@router.get("/deployments", response_model=List[Dict[str, Any]])
async def get_template_deployments():
    """
    Get template deployment history.
    
    Returns:
        List of deployment records
        
    Raises:
        HTTPException: If retrieval fails
    """
    try:
        # For now, return empty list - in production you'd store deployment history
        logger.info("Retrieved template deployment history")
        return []
    except Exception as e:
        logger.error(f"Failed to get template deployments: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get template deployments: {str(e)}"
        )


@router.get("/category/{category}", response_model=List[schemas.TemplateSuiteRead])
async def get_templates_by_category(category: str):
    """
    Retrieve all templates in a specific category.
    
    Args:
        category: The template category (e.g., "fsi_banking")
        
    Returns:
        List of templates in the specified category
        
    Raises:
        HTTPException: If template loading fails
    """
    try:
        templates = template_service.get_templates_by_category(category)
        logger.info(f"Retrieved {len(templates)} templates for category: {category}")
        return templates
    except Exception as e:
        logger.error(f"Failed to get templates for category {category}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get templates: {str(e)}"
        )


@router.get("/{template_id}", response_model=schemas.TemplateSuiteRead)
async def get_template_by_id(template_id: str):
    """
    Retrieve a specific template by ID.
    
    Args:
        template_id: The unique identifier of the template
        
    Returns:
        The template suite configuration
        
    Raises:
        HTTPException: If template not found or loading fails
    """
    try:
        template = template_service.get_template_by_id(template_id)
        if not template:
            logger.warning(f"Template not found: {template_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{template_id}' not found"
            )
        logger.info(f"Retrieved template: {template_id}")
        return template
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get template {template_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get template: {str(e)}"
        )


def _create_agent_from_template(agent_template: schemas.AgentTemplate) -> schemas.VirtualAssistantRead:
    """
    Create an agent from template configuration.
    Reuses logic from virtual_assistants.py for consistency.
    
    Args:
        agent_template: Agent template configuration
        
    Returns:
        Created agent configuration
        
    Raises:
        Exception: If agent creation fails
    """
    try:
        # Prepare sampling parameters (reusing existing logic)
        sampling_params = {
            "strategy": get_strategy(agent_template.temperature, agent_template.top_p),
            "max_tokens": agent_template.max_tokens,
            "repetition_penalty": agent_template.repetition_penalty,
        }

        # Prepare tools (reusing existing logic)
        tools = []
        for tool_info in agent_template.tools:
            if tool_info.toolgroup_id == "builtin::rag":
                if len(agent_template.knowledge_base_ids) > 0:
                    tool_dict = {
                        "name": "builtin::rag",
                        "args": {
                            "vector_db_ids": list(agent_template.knowledge_base_ids),
                        },
                    }
                    tools.append(tool_dict)
            else:
                tools.append(tool_info.toolgroup_id)

        # Create agent configuration (reusing existing logic)
        agent_config = AgentUtils.get_agent_config(
            model=agent_template.model_name,
            instructions=agent_template.prompt,
            tools=tools,
            sampling_params=sampling_params,
            max_infer_iters=agent_template.max_infer_iters,
            input_shields=agent_template.input_shields,
            output_shields=agent_template.output_shields,
        )
        agent_config["name"] = agent_template.name

        # Create agent in LlamaStack (reusing existing logic)
        agentic_system_create_response = client.agents.create(
            agent_config=agent_config,
        )

        # Return agent configuration with persona information
        return schemas.VirtualAssistantRead(
            id=agentic_system_create_response.agent_id,
            name=agent_template.name,
            input_shields=agent_template.input_shields,
            output_shields=agent_template.output_shields,
            prompt=agent_template.prompt,
            model_name=agent_template.model_name,
            knowledge_base_ids=agent_template.knowledge_base_ids,
            tools=agent_template.tools,
            # Add persona information to metadata
            metadata={"persona": agent_template.persona} if agent_template.persona else {}
        )

    except Exception as e:
        logger.error(f"Failed to create agent {agent_template.name}: {str(e)}")
        raise


@router.post("/{template_id}/deploy", response_model=schemas.TemplateDeployResponse)
async def deploy_template(
    template_id: str,
    request: schemas.TemplateDeployRequest
):
    """
    Deploy agents from a template.
    
    Args:
        template_id: The template to deploy
        request: Deployment configuration including selected agents
        
    Returns:
        Deployment results with created agents and any failures
        
    Raises:
        HTTPException: If template not found or deployment fails
    """
    try:
        logger.info(f"=== DEBUG: deploy_template() called with template_id={template_id} ===")
        logger.info(f"=== DEBUG: request={request} ===")
        
        # Get the template
        template = template_service.get_template_by_id(template_id)
        if not template:
            logger.error(f"Template not found: {template_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{template_id}' not found"
            )
        
        logger.info(f"=== DEBUG: Found template: {template.name} ===")
        
        # Determine which agents to deploy
        agents_to_deploy = template.agents
        if request.selected_agents:
            # Filter to only selected agents
            selected_names = set(request.selected_agents)
            agents_to_deploy = [agent for agent in template.agents if agent.name in selected_names]
            logger.info(f"=== DEBUG: Deploying {len(agents_to_deploy)} selected agents out of {len(template.agents)} total ===")
        else:
            logger.info(f"=== DEBUG: Deploying all {len(agents_to_deploy)} agents ===")
        
        if not agents_to_deploy:
            logger.error("No agents to deploy")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No agents to deploy"
            )
        
        # Deploy each agent
        deployed_agents = []
        failed_agents = []
        
        for agent_template in agents_to_deploy:
            try:
                logger.info(f"=== DEBUG: Deploying agent: {agent_template.name} ===")
                
                # Create agent with template metadata
                agent = _create_agent_from_template(agent_template)
                
                # Create new agent instance with updated metadata
                updated_metadata = {
                    **(agent.metadata or {}),  # Keep existing metadata (like persona)
                    "template_id": template_id,
                    "template_name": template.name,
                    "deployed_from_template": True,
                    "deployment_timestamp": datetime.now().isoformat()
                }
                
                # Create new agent instance with updated metadata
                agent = schemas.VirtualAssistantRead(
                    id=agent.id,
                    name=agent.name,
                    input_shields=agent.input_shields,
                    output_shields=agent.output_shields,
                    prompt=agent.prompt,
                    model_name=agent.model_name,
                    knowledge_base_ids=agent.knowledge_base_ids,
                    tools=agent.tools,
                    metadata=updated_metadata
                )
                
                deployed_agents.append(agent)
                logger.info(f"=== DEBUG: Successfully deployed agent: {agent.name} (ID: {agent.id}) ===")
                
            except Exception as e:
                logger.error(f"Failed to deploy agent {agent_template.name}: {str(e)}")
                failed_agents.append({
                    "name": agent_template.name,
                    "error": str(e)
                })
        
        # Create deployment summary
        deployment_summary = {
            "template_id": template_id,
            "template_name": template.name,
            "total_agents": len(agents_to_deploy),
            "successful_deployments": len(deployed_agents),
            "failed_deployments": len(failed_agents),
            "deployment_time": datetime.now().isoformat(),
            "success_rate": (len(deployed_agents) / len(agents_to_deploy)) * 100 if agents_to_deploy else 0
        }
        
        logger.info(f"=== DEBUG: Deployment complete. Success: {len(deployed_agents)}, Failed: {len(failed_agents)} ===")
        
        return schemas.TemplateDeployResponse(
            deployed_agents=deployed_agents,
            failed_agents=failed_agents,
            template_id=template_id,
            deployment_summary=deployment_summary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in deploy_template: {str(e)}")
        import traceback
        logger.error(f"=== DEBUG: Full traceback: {traceback.format_exc()} ===")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deployment failed: {str(e)}"
        )


@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh_templates():
    """
    Force refresh the template cache.
    
    Returns:
        Success message
        
    Raises:
        HTTPException: If refresh fails
    """
    try:
        template_service.refresh_cache()
        logger.info("Template cache refreshed successfully")
        return {"message": "Template cache refreshed successfully"}
    except Exception as e:
        logger.error(f"Failed to refresh template cache: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh template cache: {str(e)}"
        ) 