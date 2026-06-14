"""Configuration loader for AI providers from environment variables."""

import os
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field

from services.ai_provider.base import ProviderType, ProviderConfig
from services.ai_provider.manager import ProviderManager, ProviderManagerConfig, RoutingStrategy


@dataclass
class ProviderEnvConfig:
    """Environment variable configuration for a single provider."""
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    timeout: float = 60.0
    max_retries: int = 3
    retry_delay: float = 1.0
    max_backoff: float = 60.0
    enabled: bool = True
    priority: int = 0
    rate_limit: Optional[int] = None
    custom_headers: Dict[str, str] = field(default_factory=dict)


class EnvConfigLoader:
    """Load provider configuration from environment variables.
    
    Environment variable naming convention:
        {PROVIDER}_{SETTING}
        
    Examples:
        OPENAI_API_KEY
        OPENAI_BASE_URL
        OPENAI_MODEL
        OPENAI_TIMEOUT
        GEMINI_API_KEY
        CLAUDE_API_KEY
        OLLAMA_BASE_URL
        etc.
    """
    
    # Mapping of provider types to their env var prefix
    PROVIDER_PREFIXES = {
        ProviderType.GEMINI: "GEMINI",
        ProviderType.OPENAI: "OPENAI",
        ProviderType.CLAUDE: "ANTHROPIC",  # Anthropic API key
        ProviderType.OLLAMA: "OLLAMA",
        ProviderType.QWEN: "QWEN",
        ProviderType.LLAMA: "LLAMA",
        ProviderType.GEMMA: "GEMMA",
        ProviderType.MISTRAL: "MISTRAL",
    }
    
    # Mapping of setting names to their env var suffixes and types
    SETTING_MAPPINGS = {
        "api_key": ("API_KEY", str, None),
        "base_url": ("BASE_URL", str, None),
        "model": ("MODEL", str, None),
        "timeout": ("TIMEOUT", float, 60.0),
        "max_retries": ("MAX_RETRIES", int, 3),
        "retry_delay": ("RETRY_DELAY", float, 1.0),
        "max_backoff": ("MAX_BACKOFF", float, 60.0),
        "enabled": ("ENABLED", bool, True),
        "priority": ("PRIORITY", int, 0),
        "rate_limit": ("RATE_LIMIT", int, None),
    }
    
    def __init__(self, prefix: str = "AI_"):
        """Initialize the config loader.
        
        Args:
            prefix: Prefix for all environment variables (default: "AI_")
        """
        self.prefix = prefix
    
    def load_provider_config(
        self,
        provider_type: ProviderType
    ) -> Optional[ProviderConfig]:
        """Load configuration for a specific provider from environment variables.
        
        Args:
            provider_type: The provider type to load config for
            
        Returns:
            ProviderConfig if any configuration is found, None otherwise
        """
        env_prefix = self.PROVIDER_PREFIXES.get(provider_type)
        if not env_prefix:
            return None
        
        # Check if any environment variable exists for this provider
        prefix_str = f"{self.prefix}{env_prefix}_"
        has_config = any(
            k.startswith(prefix_str) or k == f"{self.prefix}{env_prefix}API_KEY"
            for k in os.environ.keys()
        )
        
        if not has_config:
            return None
        
        config = ProviderConfig(provider_type=provider_type)
        
        # Load each setting from environment
        for setting_name, (suffix, type_func, default) in self.SETTING_MAPPINGS.items():
            env_key = f"{self.prefix}{env_prefix}_{suffix}"
            env_value = os.getenv(env_key)
            
            if env_value is not None:
                try:
                    if type_func == bool:
                        setattr(config, setting_name, env_value.lower() in ('true', '1', 'yes'))
                    else:
                        setattr(config, setting_name, type_func(env_value))
                except (ValueError, TypeError):
                    if default is not None:
                        setattr(config, setting_name, default)
            elif default is not None:
                setattr(config, setting_name, default)
        
        return config
    
    def load_all_configs(self) -> List[ProviderConfig]:
        """Load configuration for all configured providers.
        
        Returns:
            List of ProviderConfig objects for configured providers
        """
        configs = []
        
        for provider_type in ProviderType:
            config = self.load_provider_config(provider_type)
            if config:
                configs.append(config)
        
        return configs
    
    def create_provider_manager(
        self,
        routing_strategy: Optional[RoutingStrategy] = None,
        default_timeout: Optional[float] = None,
        enable_fallback: bool = True,
    ) -> ProviderManager:
        """Create a configured provider manager from environment variables.
        
        Args:
            routing_strategy: Routing strategy to use
            default_timeout: Default timeout for requests
            enable_fallback: Whether to enable automatic fallback
            
        Returns:
            Configured ProviderManager instance
        """
        from services.ai_provider.manager import create_provider
        
        # Manager configuration
        manager_config = ProviderManagerConfig()
        
        if routing_strategy:
            manager_config.routing_strategy = routing_strategy
        if default_timeout:
            manager_config.default_timeout = default_timeout
        manager_config.enable_fallback = enable_fallback
        
        # Check for manager-level settings
        if os.getenv(f"{self.prefix}ROUTING_STRATEGY"):
            try:
                manager_config.routing_strategy = RoutingStrategy(
                    os.getenv(f"{self.prefix}ROUTING_STRATEGY").lower()
                )
            except ValueError:
                pass
        
        manager = ProviderManager(manager_config)
        
        # Load and register providers
        for config in self.load_all_configs():
            try:
                provider = create_provider(config)
                manager.register_provider_instance(
                    provider,
                    config,
                    set_as_default=(config.priority == 0)
                )
            except Exception as e:
                import logging
                logging.warning(f"Failed to create provider {config.provider_type.value}: {e}")
        
        return manager


# Convenience functions for common operations
def load_providers_from_env() -> ProviderManager:
    """Load all configured providers from environment variables.
    
    Returns:
        Configured ProviderManager
    """
    loader = EnvConfigLoader()
    return loader.create_provider_manager()


def get_provider_config(provider_type: ProviderType) -> Optional[ProviderConfig]:
    """Get configuration for a specific provider from environment.
    
    Args:
        provider_type: Provider type to get config for
        
    Returns:
        ProviderConfig or None
    """
    loader = EnvConfigLoader()
    return loader.load_provider_config(provider_type)


# Environment variable documentation
ENV_VAR_DOCS = """
AI Provider Environment Variables
=================================

Global Settings:
    AI_ROUTING_STRATEGY    - Routing strategy: priority, latency, cost, round_robin, random
    AI_DEFAULT_TIMEOUT     - Default request timeout in seconds

Provider Settings:
    {PROVIDER}_API_KEY      - API key for the provider
    {PROVIDER}_BASE_URL     - Custom base URL (optional)
    {PROVIDER}_MODEL        - Default model to use
    {PROVIDER}_TIMEOUT      - Request timeout in seconds
    {PROVIDER}_MAX_RETRIES  - Maximum retry attempts
    {PROVIDER}_RETRY_DELAY  - Initial retry delay in seconds
    {PROVIDER}_MAX_BACKOFF  - Maximum retry delay in seconds
    {PROVIDER}_ENABLED      - Whether provider is enabled (true/false)
    {PROVIDER}_PRIORITY     - Provider priority (lower = higher priority)
    {PROVIDER}_RATE_LIMIT   - Requests per minute limit

Provider Prefixes:
    GEMINI     - Google Gemini
    OPENAI     - OpenAI
    ANTHROPIC  - Anthropic Claude
    OLLAMA     - Ollama (local models)
    QWEN       - Alibaba Qwen
    LLAMA      - Meta Llama
    GEMMA      - Google Gemma
    MISTRAL    - Mistral AI

Example Configuration (.env):
----------------------------
# Primary provider
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
OPENAI_PRIORITY=0

# Fallback providers
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_PRIORITY=1

GEMINI_API_KEY=...
GEMINI_PRIORITY=2

# Local Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
OLLAMA_PRIORITY=3

# Routing
AI_ROUTING_STRATEGY=priority
AI_DEFAULT_TIMEOUT=60
"""


def print_env_docs():
    """Print environment variable documentation."""
    print(ENV_VAR_DOCS)


if __name__ == "__main__":
    print_env_docs()