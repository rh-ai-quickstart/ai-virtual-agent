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


class ChatSamplingParams(BaseModel):
    """Chat sampling parameters configuration"""
    strategy: str = Field(default="greedy", description="Sampling strategy: greedy or top_p")
    max_tokens: int = Field(default=512, description="Maximum tokens for response")
    temperature: float = Field(default=0.0, description="Temperature for top_p strategy")
    top_p: float = Field(default=0.95, description="Top_p value for top_p strategy")


class ChatAgentTypeConfig(BaseModel):
    """Chat agent type configuration"""
    sampling_params: ChatSamplingParams = Field(default_factory=ChatSamplingParams)
    response_format: Optional[Dict[str, Any]] = Field(default=None, description="Response format for ReAct agents")


class ChatSessionConfig(BaseModel):
    """Chat session configuration"""
    default_session_name_prefix: str = Field(default="Chat", description="Default session name prefix")
    session_name_length: int = Field(default=4, description="Random suffix length")
    session_name_chars: str = Field(default="abcdefghijklmnopqrstuvwxyz0123456789", description="Characters for session name")


class ChatResponseFormatting(BaseModel):
    """Chat response formatting configuration"""
    tool_results_header: str = Field(default="**Here's what I found:**", description="Header for tool results")
    web_search_tool_name: str = Field(default="web_search", description="Web search tool name")
    error_prefix: str = Field(default="🚨 Llama Stack server Error:", description="Error message prefix")
    final_answer_prefix: str = Field(default=" **Final Answer:**", description="Final answer prefix")


class ChatErrorHandling(BaseModel):
    """Chat error handling configuration"""
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_delay_seconds: int = Field(default=1, description="Delay between retries")
    timeout_seconds: int = Field(default=30, description="Request timeout")


class ChatConfig(BaseModel):
    """Chat configuration settings"""
    default_sampling_params: ChatSamplingParams = Field(default_factory=ChatSamplingParams)
    default_instructions: str = Field(
        default="You are a helpful assistant. When you use a tool always respond with a summary of the result.",
        description="Default instructions for agents"
    )
    agent_types: Dict[str, ChatAgentTypeConfig] = Field(
        default_factory=lambda: {
            "react": ChatAgentTypeConfig(),
            "regular": ChatAgentTypeConfig()
        },
        description="Agent type configurations"
    )
    session: ChatSessionConfig = Field(default_factory=ChatSessionConfig)
    response_formatting: ChatResponseFormatting = Field(default_factory=ChatResponseFormatting)
    error_handling: ChatErrorHandling = Field(default_factory=ChatErrorHandling)


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
    chat: ChatConfig = Field(default_factory=ChatConfig)


class ConfigManager:
    """Configuration manager for loading and accessing application settings"""
    
    def __init__(self, config_file: Optional[str] = None, chat_config_file: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Path to main configuration file (optional)
            chat_config_file: Path to chat configuration file (optional)
        """
        self.config_file = config_file or self._find_config_file()
        self.chat_config_file = chat_config_file or self._find_chat_config_file()
        self._config: Optional[AppConfig] = None
        self._chat_config: Optional[ChatConfig] = None
        
    def _find_config_file(self) -> str:
        """Find the main configuration file in the expected locations"""
        # Look for config file in order of preference
        search_paths = [
            "backend/config/template_config.yaml",
            "config/template_config.yaml", 
            "template_config.yaml"
        ]
        
        for path in search_paths:
            if os.path.exists(path):
                logger.info(f"Found main config file: {path}")
                return path
        
        # If no config file found, use defaults
        logger.warning("No main config file found, using default configuration")
        return ""
    
    def _find_chat_config_file(self) -> str:
        """Find the chat configuration file in the expected locations"""
        # Look for chat config file in order of preference
        search_paths = [
            "backend/config/chat_config.yaml",
            "config/chat_config.yaml", 
            "chat_config.yaml"
        ]
        
        for path in search_paths:
            if os.path.exists(path):
                logger.info(f"Found chat config file: {path}")
                return path
        
        # If no chat config file found, use defaults
        logger.warning("No chat config file found, using default configuration")
        return ""
    
    def load_config(self) -> AppConfig:
        """Load main configuration from file or use defaults"""
        if self._config is not None:
            return self._config
            
        if self.config_file and os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as file:
                    config_data = yaml.safe_load(file)
                    self._config = AppConfig(**config_data)
                    logger.info(f"Loaded main configuration from {self.config_file}")
            except Exception as e:
                logger.error(f"Failed to load main config file {self.config_file}: {str(e)}")
                logger.info("Using default main configuration")
                self._config = AppConfig()
        else:
            logger.info("Using default main configuration")
            self._config = AppConfig()
        
        return self._config
    
    def load_chat_config(self) -> ChatConfig:
        """Load chat configuration from file or use defaults"""
        if self._chat_config is not None:
            return self._chat_config
            
        if self.chat_config_file and os.path.exists(self.chat_config_file):
            try:
                with open(self.chat_config_file, 'r', encoding='utf-8') as file:
                    config_data = yaml.safe_load(file)
                    if 'chat' in config_data:
                        self._chat_config = ChatConfig(**config_data['chat'])
                        logger.info(f"Loaded chat configuration from {self.chat_config_file}")
                    else:
                        logger.warning("No 'chat' section found in chat config file, using defaults")
                        self._chat_config = ChatConfig()
            except Exception as e:
                logger.error(f"Failed to load chat config file {self.chat_config_file}: {str(e)}")
                logger.info("Using default chat configuration")
                self._chat_config = ChatConfig()
        else:
            logger.info("Using default chat configuration")
            self._chat_config = ChatConfig()
        
        return self._chat_config
    
    def get_template_config(self) -> TemplateServiceConfig:
        """Get template service configuration"""
        config = self.load_config()
        return config.template_service
    
    def get_chat_config(self) -> ChatConfig:
        """Get chat configuration"""
        return self.load_chat_config()
    
    def reload_config(self) -> None:
        """Reload all configuration from files"""
        self._config = None
        self._chat_config = None
        self.load_config()
        self.load_chat_config()
        logger.info("All configuration reloaded")


# Global configuration manager instance
config_manager = ConfigManager() 