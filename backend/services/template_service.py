"""
Template Service for managing AI agent templates.

This module provides functionality to load, validate, and manage YAML-based
agent templates. Templates define pre-configured agent suites for different
business domains and use cases.

Key Features:
- YAML template loading and validation
- Template caching for performance
- Error handling and logging
- Integration with existing LlamaStack patterns
- Fully configurable via YAML configuration files
"""

import os
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from .. import schemas
from ..config.config import config_manager
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class TemplateService:
    """Service for managing agent templates from YAML files"""
    
    def __init__(self, templates_dir: str = None):
        """
        Initialize template service.
        
        Args:
            templates_dir: Directory containing YAML template files (overrides config)
        """
        try:
            logger.info("=== DEBUG: TemplateService.__init__() called ===")
            # Load configuration
            logger.info("=== DEBUG: About to load config ===")
            self.config = config_manager.get_template_config()
            logger.info("=== DEBUG: Config loaded successfully ===")
            
            # Set templates directory (config takes precedence, then parameter, then default)
            if templates_dir is None:
                config_dir = self.config.templates_dir
                logger.info(f"=== DEBUG: Using config templates_dir: {config_dir} ===")
                if os.path.isabs(config_dir):
                    self.templates_dir = Path(config_dir)
                else:
                    # Look for templates relative to project root
                    backend_dir = Path(__file__).parent.parent  # backend/
                    project_root = backend_dir.parent  # project root
                    self.templates_dir = project_root / config_dir
                    logger.info(f"=== DEBUG: Calculated templates_dir: {self.templates_dir} ===")
            else:
                self.templates_dir = Path(templates_dir)
                logger.info(f"=== DEBUG: Using provided templates_dir: {self.templates_dir} ===")
            
            logger.info(f"=== DEBUG: Final templates_dir: {self.templates_dir} ===")
            logger.info(f"=== DEBUG: templates_dir.exists(): {self.templates_dir.exists()} ===")
            
            self.templates_dir.mkdir(exist_ok=True)
            self._templates_cache: Optional[Dict[str, schemas.TemplateSuiteRead]] = None
            self._cache_timestamp: Optional[datetime] = None
            
            logger.info(f"Template service initialized with directory: {self.templates_dir}")
        except Exception as e:
            logger.error(f"=== DEBUG: Exception in TemplateService.__init__: {str(e)} ===")
            import traceback
            logger.error(f"=== DEBUG: Full traceback: {traceback.format_exc()} ===")
            raise
        
    def _is_cache_valid(self) -> bool:
        """Check if the cache is still valid"""
        if not self.config.cache.enabled:
            return False
            
        if self._templates_cache is None or self._cache_timestamp is None:
            return False
        
        cache_age = (datetime.now() - self._cache_timestamp).total_seconds()
        return cache_age < self.config.cache.ttl_seconds
    
    def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Load and parse a YAML file with error handling"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                if not content.strip():
                    raise ValueError(f"Empty YAML file: {file_path}")
                return yaml.safe_load(content)
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {file_path}: {str(e)}")
            raise ValueError(f"Invalid YAML syntax in {file_path}: {str(e)}")
        except FileNotFoundError:
            logger.error(f"Template file not found: {file_path}")
            raise ValueError(f"Template file not found: {file_path}")
        except Exception as e:
            logger.error(f"Unexpected error loading {file_path}: {str(e)}")
            raise ValueError(f"Failed to load template file {file_path}: {str(e)}")
    
    def _validate_template_structure(self, template_data: Dict[str, Any], file_path: Path) -> Tuple[bool, List[str]]:
        """
        Validate template data structure.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        required_fields = ['id', 'name', 'description', 'category']
        
        # Check required fields
        for field in required_fields:
            if field not in template_data:
                errors.append(f"Missing required field '{field}' in template")
        
        if errors:
            return False, errors
        
        # Check personas structure (new format) - prioritize this
        if 'personas' in template_data:
            if not isinstance(template_data['personas'], dict):
                errors.append("Template 'personas' must be a dictionary")
            else:
                # Validate each persona
                for persona_key, persona_data in template_data['personas'].items():
                    persona_errors = self._validate_persona_structure(persona_data, persona_key)
                    errors.extend(persona_errors)
        # Check agents array (old format for backward compatibility)
        elif 'agents' in template_data:
            if not isinstance(template_data['agents'], list):
                errors.append("Template 'agents' must be a list")
            elif len(template_data['agents']) == 0:
                errors.append("Template must contain at least one agent")
            else:
                # Validate each agent
                for i, agent in enumerate(template_data['agents']):
                    agent_errors = self._validate_agent_structure(agent, i)
                    errors.extend(agent_errors)
        else:
            errors.append("Template must contain either 'personas' or 'agents'")
        
        return len(errors) == 0, errors
    
    def _validate_persona_structure(self, persona_data: Dict[str, Any], persona_key: str) -> List[str]:
        """Validate persona structure"""
        errors = []
        required_fields = ['label', 'description', 'agents']
        
        for field in required_fields:
            if field not in persona_data:
                errors.append(f"Persona '{persona_key}': Missing required field '{field}'")
        
        # Validate agents array within persona
        if 'agents' in persona_data:
            if not isinstance(persona_data['agents'], list):
                errors.append(f"Persona '{persona_key}': 'agents' must be a list")
            elif len(persona_data['agents']) == 0:
                errors.append(f"Persona '{persona_key}': must contain at least one agent")
            else:
                # Validate each agent in the persona
                for i, agent in enumerate(persona_data['agents']):
                    agent_errors = self._validate_agent_structure(agent, i, persona_key)
                    errors.extend(agent_errors)
        
        # Validate demo_questions if present
        if 'demo_questions' in persona_data:
            if not isinstance(persona_data['demo_questions'], list):
                errors.append(f"Persona '{persona_key}': 'demo_questions' must be a list")
        
        return errors
    
    def _validate_agent_structure(self, agent_data: Dict[str, Any], index: int, persona_key: str = None) -> List[str]:
        """Validate individual agent structure"""
        errors = []
        required_fields = ['name', 'model_name', 'prompt']
        
        for field in required_fields:
            if field not in agent_data:
                context = f"Persona '{persona_key}' Agent {index}" if persona_key else f"Agent {index}"
                errors.append(f"{context}: Missing required field '{field}'")
        
        # Validate list fields
        list_fields = ['tools', 'knowledge_base_ids', 'input_shields', 'output_shields']
        for field in list_fields:
            if field in agent_data and not isinstance(agent_data[field], list):
                context = f"Persona '{persona_key}' Agent {index}" if persona_key else f"Agent {index}"
                errors.append(f"{context}: '{field}' must be a list")
        
        # Validate numeric fields
        numeric_fields = ['temperature', 'repetition_penalty', 'max_tokens', 'top_p', 'max_infer_iters']
        for field in numeric_fields:
            if field in agent_data and not isinstance(agent_data[field], (int, float)):
                context = f"Persona '{persona_key}' Agent {index}" if persona_key else f"Agent {index}"
                errors.append(f"{context}: '{field}' must be a number")
        
        return errors
    
    def _convert_to_schema(self, template_data: Dict[str, Any]) -> schemas.TemplateSuiteRead:
        """Convert template data to schema with configuration-based defaults"""
        try:
            # Get default settings from configuration
            defaults = self.config.default_agent_settings
            
            # Convert agents to AgentTemplate schemas
            agents = []
            persona_count = 0
            agent_count = 0
            
            # Handle new personas structure
            if 'personas' in template_data:
                persona_count = len(template_data['personas'])
                for persona_key, persona_data in template_data['personas'].items():
                    for agent_data in persona_data['agents']:
                        agent = schemas.AgentTemplate(
                            name=agent_data['name'],
                            description=agent_data.get('description'),
                            model_name=agent_data['model_name'],
                            prompt=agent_data['prompt'],
                            persona=persona_key,  # Set persona from the structure
                            tools=agent_data.get('tools', defaults.tools),
                            knowledge_base_ids=agent_data.get('knowledge_base_ids', defaults.knowledge_base_ids),
                            temperature=agent_data.get('temperature', defaults.temperature),
                            repetition_penalty=agent_data.get('repetition_penalty', defaults.repetition_penalty),
                            max_tokens=agent_data.get('max_tokens', defaults.max_tokens),
                            top_p=agent_data.get('top_p', defaults.top_p),
                            max_infer_iters=agent_data.get('max_infer_iters', defaults.max_infer_iters),
                            input_shields=agent_data.get('input_shields', defaults.input_shields),
                            output_shields=agent_data.get('output_shields', defaults.output_shields)
                        )
                        agents.append(agent)
                        agent_count += 1
            # Handle old agents structure for backward compatibility
            elif 'agents' in template_data:
                agent_count = len(template_data['agents'])
                for agent_data in template_data['agents']:
                    agent = schemas.AgentTemplate(
                        name=agent_data['name'],
                        description=agent_data.get('description'),
                        model_name=agent_data['model_name'],
                        prompt=agent_data['prompt'],
                        persona=agent_data.get('persona'),
                        tools=agent_data.get('tools', defaults.tools),
                        knowledge_base_ids=agent_data.get('knowledge_base_ids', defaults.knowledge_base_ids),
                        temperature=agent_data.get('temperature', defaults.temperature),
                        repetition_penalty=agent_data.get('repetition_penalty', defaults.repetition_penalty),
                        max_tokens=agent_data.get('max_tokens', defaults.max_tokens),
                        top_p=agent_data.get('top_p', defaults.top_p),
                        max_infer_iters=agent_data.get('max_infer_iters', defaults.max_infer_iters),
                        input_shields=agent_data.get('input_shields', defaults.input_shields),
                        output_shields=agent_data.get('output_shields', defaults.output_shields)
                    )
                    agents.append(agent)
            
            # Update metadata with calculated counts
            metadata = template_data.get('metadata', {}).copy()
            metadata['persona_count'] = persona_count
            metadata['agent_count'] = agent_count
            
            logger.info(f"Converting template {template_data.get('name', 'unknown')}: {persona_count} personas, {agent_count} agents")
            
            return schemas.TemplateSuiteRead(
                id=template_data['id'],
                name=template_data['name'],
                description=template_data['description'],
                category=template_data['category'],
                agents=agents,
                metadata=metadata,  # Use updated metadata with correct counts
                personas=template_data.get('personas', {}),  # Include personas data
                industry_id=template_data.get('industry_id'),  # Make it optional
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
        except Exception as e:
            logger.error(f"Failed to convert template data to schema: {str(e)}")
            raise ValueError(f"Template conversion failed: {str(e)}")
    
    def load_templates(self, force_reload: bool = False) -> List[schemas.TemplateSuiteRead]:
        """
        Load all templates from the templates directory.
        
        Args:
            force_reload: Force reload templates from disk (bypass cache)
            
        Returns:
            List of template suites
            
        Raises:
            ValueError: If template loading fails
        """
        try:
            logger.info("=== DEBUG: load_templates() called ===")
            
            # Check cache first
            if not force_reload and self._is_cache_valid():
                logger.debug("Returning cached templates")
                return list(self._templates_cache.values())
            
            logger.info(f"Loading templates from disk: {self.templates_dir}")
            templates = []
            errors = []
            
            # Load all YAML files from templates directory
            yaml_files = list(self.templates_dir.glob("*.yaml"))
            logger.info(f"Found {len(yaml_files)} YAML files: {[f.name for f in yaml_files]}")
            
            if not yaml_files:
                logger.warning(f"No YAML template files found in {self.templates_dir}")
                return []
            
            for yaml_file in yaml_files:
                try:
                    logger.info(f"Processing template file: {yaml_file}")
                    template_data = self._load_yaml_file(yaml_file)
                    logger.info(f"Loaded YAML data for {yaml_file.name}")
                    
                    is_valid, validation_errors = self._validate_template_structure(template_data, yaml_file)
                    if is_valid:
                        logger.info(f"Template {yaml_file.name} is valid, converting to schema...")
                        template_schema = self._convert_to_schema(template_data)
                        templates.append(template_schema)
                        logger.info(f"Successfully loaded template: {template_schema.name} ({template_schema.id})")
                    else:
                        error_msg = f"Invalid template structure in {yaml_file}: {'; '.join(validation_errors)}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                        
                except Exception as e:
                    error_msg = f"Failed to load template from {yaml_file}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                    continue
            
            # Update cache
            self._templates_cache = {template.id: template for template in templates}
            self._cache_timestamp = datetime.now()
            
            logger.info(f"Template loading completed. Loaded {len(templates)} templates, {len(errors)} errors")
            
            if errors:
                logger.warning(f"Template loading completed with {len(errors)} errors")
            else:
                logger.info(f"Successfully loaded {len(templates)} templates")
            
            return templates
        except Exception as e:
            logger.error(f"=== DEBUG: Exception in load_templates: {str(e)} ===")
            import traceback
            logger.error(f"=== DEBUG: Full traceback: {traceback.format_exc()} ===")
            raise
    
    def get_template_by_id(self, template_id: str) -> Optional[schemas.TemplateSuiteRead]:
        """Get template by ID"""
        templates = self.load_templates()
        return next((t for t in templates if t.id == template_id), None)
    
    def get_template_by_category(self, category: str) -> Optional[schemas.TemplateSuiteRead]:
        """Get template by category"""
        templates = self.load_templates()
        return next((t for t in templates if t.category == category), None)
    
    def get_templates_by_category(self, category: str) -> List[schemas.TemplateSuiteRead]:
        """Get all templates in a specific category"""
        templates = self.load_templates()
        return [t for t in templates if t.category == category]
    
    def get_categories(self) -> List[str]:
        """Get all unique categories"""
        templates = self.load_templates()
        return list(set(t.category for t in templates))
    
    def refresh_cache(self) -> None:
        """Force refresh the template cache"""
        self._templates_cache = None
        self._cache_timestamp = None
        logger.info("Template cache refreshed")
    
    def reload_config(self) -> None:
        """Reload configuration and refresh cache"""
        self.config = config_manager.get_template_config()
        self.refresh_cache()
        logger.info("Template service configuration reloaded")


# Global instance
template_service = TemplateService() 