"""
Template loader utility for reading agent templates from YAML files.

This module provides functionality to load agent template configurations
from YAML files in the agent_templates directory.
"""

from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel

from ..utils.logging_config import get_logger


class AgentTemplate(BaseModel):
    """Schema for agent template configuration."""

    name: str
    persona: str
    prompt: str
    model_name: str
    tools: List[Dict[str, str]]
    knowledge_base_ids: List[str]
    knowledge_base_config: Optional[Dict] = None
    demo_questions: Optional[List[str]] = None


logger = get_logger(__name__)


def load_template_from_yaml(file_path: str) -> Dict:
    """
    Load a single template suite from a YAML file.

    Args:
        file_path: Path to the YAML file

    Returns:
        Dictionary containing the suite configuration

    Raises:
        FileNotFoundError: If file doesn't exist
        yaml.YAMLError: If YAML parsing fails
    """
    try:
        with open(file_path, "r") as file:
            config = yaml.safe_load(file)
        logger.debug(f"Loaded template from {file_path}")
        logger.debug(f"Config keys: {list(config.keys()) if config else 'None'}")
        return config
    except FileNotFoundError:
        logger.error(f"Template file not found: {file_path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file {file_path}: {e}")
        raise


def convert_yaml_template_to_agent_template(
    yaml_template: Dict,
) -> AgentTemplate:
    """
    Convert YAML template configuration to AgentTemplate object.

    Args:
        yaml_template: Template configuration from YAML

    Returns:
        AgentTemplate object
    """
    return AgentTemplate(
        name=yaml_template["name"],
        persona=yaml_template["persona"],
        prompt=yaml_template["prompt"],
        model_name=yaml_template["model_name"],
        tools=yaml_template["tools"],
        knowledge_base_ids=yaml_template["knowledge_base_ids"],
        knowledge_base_config=yaml_template.get("knowledge_base_config"),
        demo_questions=yaml_template.get("demo_questions"),
    )


def load_all_templates_from_directory(templates_dir: str = "agent_templates"):
    """
    Load all template suites from the agent_templates directory.

    Args:
        templates_dir: Directory containing YAML template files

    Returns:
        Dictionary with suite configurations
    """
    templates_path = Path(__file__).parent.parent / templates_dir
    logger.info(f"Looking for templates in: {templates_path}")

    if not templates_path.exists():
        logger.warning(f"Templates directory not found: {templates_path}")
        return ({}, {})

    all_suites = {}
    all_templates = {}

    # Load all YAML files in the directory
    yaml_files = list(templates_path.glob("*.yaml"))
    logger.info(f"Found {len(yaml_files)} YAML files: {[f.name for f in yaml_files]}")

    for yaml_file in yaml_files:
        try:
            logger.info(f"Loading template from: {yaml_file}")
            suite_config = load_template_from_yaml(str(yaml_file))
            suite_id = yaml_file.stem

            # Convert YAML templates to AgentTemplate objects
            templates = {}
            logger.info(
                f"Processing {len(suite_config.get('templates', {}))} "
                f"templates in suite {suite_id}"
            )
            for template_id, template_config in suite_config.get(
                "templates", {}
            ).items():
                logger.debug(f"Converting template: {template_id}")
                agent_template = convert_yaml_template_to_agent_template(
                    template_config
                )
                templates[template_id] = agent_template
                all_templates[template_id] = agent_template

            # Create suite configuration
            suite_info = {
                "name": suite_config["name"],
                "description": suite_config["description"],
                "category": suite_config["category"],
                "templates": templates,
            }

            all_suites[suite_id] = suite_info
            logger.info(f"Loaded suite '{suite_id}' with {len(templates)} templates")

        except Exception as e:
            logger.error(f"Failed to load template from {yaml_file}: {str(e)}")
            continue

    logger.info(
        f"Loaded {len(all_suites)} suites with {len(all_templates)} total templates"
    )
    return (all_suites, all_templates)


def get_suites_by_category(all_suites: Dict) -> Dict[str, List[str]]:
    """
    Group suites by category.

    Args:
        all_suites: Dictionary of all suites

    Returns:
        Dictionary with categories as keys and lists of suite IDs as values
    """
    categories = {}
    for suite_id, suite_config in all_suites.items():
        category = suite_config["category"]
        if category not in categories:
            categories[category] = []
        categories[category].append(suite_id)
    return categories
