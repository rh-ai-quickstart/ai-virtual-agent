"""
Configuration management for the AI Virtual Agent platform.

This module provides centralized configuration loading and management
for all application settings, ensuring no hardcoded values.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from pydantic import BaseModel, Field

from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class CacheConfig(BaseModel):
    """Cache configuration settings"""
    ttl_seconds: int = Field(default=300, description="Cache TTL in seconds")
    enabled: bool = Field(default=True, description="Whether caching is enabled")


class DefaultAgentSettings(BaseModel):
    """Default agent configuration settings"""
    temperature: float = Field(default=0.1, description="Default temperature")
    repetition_penalty: float = Field(default=1.0, description="Default repetition penalty")
    max_tokens: int = Field(default=4096, description="Default max tokens")
    top_p: float = Field(default=0.95, description="Default top_p")
    max_infer_iters: int = Field(default=10, description="Default max inference iterations")
    input_shields: list = Field(default_factory=list, description="Default input shields")
    output_shields: list = Field(default_factory=list, description="Default output shields")
    knowledge_base_ids: list = Field(default_factory=list, description="Default knowledge base IDs")
    tools: list = Field(default_factory=list, description="Default tools")


class ValidationConfig(BaseModel):
    """Validation configuration settings"""
    required_template_fields: list = Field(default_factory=lambda: ["id", "name", "description", "category", "agents"])
    required_agent_fields: list = Field(default_factory=lambda: ["name", "model_name", "prompt"])
    numeric_agent_fields: list = Field(default_factory=lambda: ["temperature", "repetition_penalty", "max_tokens", "top_p", "max_infer_iters"])
    list_agent_fields: list = Field(default_factory=lambda: ["tools", "knowledge_base_ids", "input_shields", "output_shields"])


class DeploymentConfig(BaseModel):
    """Deployment configuration settings"""
    max_agents_per_deployment: int = Field(default=10, description="Maximum agents per deployment")
    timeout_seconds: int = Field(default=300, description="Deployment timeout in seconds")
    retry_attempts: int = Field(default=3, description="Number of retry attempts")


class TemplateServiceConfig(BaseModel):
    """Template service configuration"""
    templates_dir: str = Field(default="templates", description="Templates directory path")
    cache: CacheConfig = Field(default_factory=CacheConfig)
    default_agent_settings: DefaultAgentSettings = Field(default_factory=DefaultAgentSettings)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    deployment: DeploymentConfig = Field(default_factory=DeploymentConfig)


class AppConfig(BaseModel):
    """Main application configuration"""
    template_service: TemplateServiceConfig = Field(default_factory=TemplateServiceConfig)


class ConfigManager:
    """Configuration manager for loading and accessing application settings"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Path to configuration file (optional)
        """
        self.config_file = config_file or self._find_config_file()
        self._config: Optional[AppConfig] = None
        
    def _find_config_file(self) -> str:
        """Find the configuration file in the expected locations"""
        # Look for config file in order of preference
        search_paths = [
            "backend/config/template_config.yaml",
            "config/template_config.yaml", 
            "template_config.yaml"
        ]
        
        for path in search_paths:
            if os.path.exists(path):
                logger.info(f"Found config file: {path}")
                return path
        
        # If no config file found, use defaults
        logger.warning("No config file found, using default configuration")
        return ""
    
    def load_config(self) -> AppConfig:
        """Load configuration from file or use defaults"""
        if self._config is not None:
            return self._config
            
        if self.config_file and os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as file:
                    config_data = yaml.safe_load(file)
                    self._config = AppConfig(**config_data)
                    logger.info(f"Loaded configuration from {self.config_file}")
            except Exception as e:
                logger.error(f"Failed to load config file {self.config_file}: {str(e)}")
                logger.info("Using default configuration")
                self._config = AppConfig()
        else:
            logger.info("Using default configuration")
            self._config = AppConfig()
        
        return self._config
    
    def get_template_config(self) -> TemplateServiceConfig:
        """Get template service configuration"""
        config = self.load_config()
        return config.template_service
    
    def reload_config(self) -> None:
        """Reload configuration from file"""
        self._config = None
        self.load_config()
        logger.info("Configuration reloaded")


# Global configuration manager instance
config_manager = ConfigManager() 