"""Provider Manager - Handles routing, fallback, and retry logic."""

import asyncio
import os
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable, TypeVar, Union
from datetime import datetime
from enum import Enum

from services.ai_provider.base import (
    BaseAIProvider,
    ProviderType,
    ProviderConfig,
    ProviderStatus,
    ProviderHealth,
    Message,
    FunctionDefinition,
    ChatCompletionResponse,
    StreamingChunk,
    StreamingResponse,
    AIProviderError,
    AllProvidersFailedError,
    RateLimitError,
    TimeoutError,
    AuthenticationError,
    ModelInfo,
)
from services.ai_provider.utils import RetryConfig, retry_async, calculate_delay, CircuitBreaker
from services.ai_provider.logging_config import AIProviderLogger, get_logger


T = TypeVar('T')


class RoutingStrategy(Enum):
    """Strategy for routing requests to providers."""
    PRIORITY = "priority"  # Use providers in priority order
    LATENCY = "latency"  # Use fastest provider
    COST = "cost"  # Use cheapest provider
    ROUND_ROBIN = "round_robin"  # Distribute across providers
    RANDOM = "random"  # Random selection


@dataclass
class ProviderManagerConfig:
    """Configuration for the provider manager."""
    default_timeout: float = 60.0
    default_max_retries: int = 3
    default_retry_delay: float = 1.0
    max_backoff: float = 60.0
    enable_fallback: bool = True
    enable_circuit_breaker: bool = True
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 60.0
    routing_strategy: RoutingStrategy = RoutingStrategy.PRIORITY
    log_level: str = "INFO"


@dataclass
class ProviderRegistration:
    """Registration info for a provider."""
    provider: BaseAIProvider
    config: ProviderConfig
    circuit_breaker: CircuitBreaker
    request_count: int = 0
    last_used: Optional[datetime] = None


class ProviderManager:
    """Manages multiple AI providers with routing, fallback, and retry logic.
    
    This is the central component that coordinates all provider interactions,
    handling provider selection, automatic failover, and request retrying.
    """
    
    # Mapping from provider type to provider class
    PROVIDER_CLASSES = {}
    
    def __init__(self, config: Optional[ProviderManagerConfig] = None):
        """Initialize the provider manager.
        
        Args:
            config: Optional configuration for the manager
        """
        self.config = config or ProviderManagerConfig()
        self.logger = get_logger()
        
        self._providers: Dict[ProviderType, ProviderRegistration] = {}
        self._default_provider: Optional[ProviderType] = None
        self._round_robin_index: Dict[ProviderType, int] = {}
        self._fallback_order: List[ProviderType] = []
        self._lock = asyncio.Lock()
    
    @classmethod
    def register_provider(cls, provider_type: ProviderType):
        """Decorator to register a provider class.
        
        Args:
            provider_type: The type to register
            
        Returns:
            Decorator function
        """
        def decorator(provider_class):
            cls.PROVIDER_CLASSES[provider_type] = provider_class
            return provider_class
        return decorator
    
    def register_provider_instance(
        self,
        provider: BaseAIProvider,
        config: ProviderConfig,
        set_as_default: bool = False,
    ) -> None:
        """Register a provider instance.
        
        Args:
            provider: Provider instance
            config: Provider configuration
            set_as_default: Whether to set this as the default provider
        """
        provider_type = provider.provider_type
        
        circuit_breaker = CircuitBreaker(
            failure_threshold=self.config.circuit_breaker_threshold,
            recovery_timeout=self.config.circuit_breaker_timeout,
        )
        
        self._providers[provider_type] = ProviderRegistration(
            provider=provider,
            config=config,
            circuit_breaker=circuit_breaker,
        )
        
        self._round_robin_index[provider_type] = 0
        
        if set_as_default or self._default_provider is None:
            self._default_provider = provider_type
        
        self._update_fallback_order()
    
    def _update_fallback_order(self) -> None:
        """Update the fallback order based on provider priorities."""
        sorted_providers = sorted(
            self._providers.items(),
            key=lambda x: x[1].config.priority
        )
        self._fallback_order = [p[0] for p in sorted_providers]
    
    def _get_provider_for_routing(
        self,
        preferred_provider: Optional[ProviderType] = None,
        requires_vision: bool = False,
        requires_function_calling: bool = False,
    ) -> Optional[ProviderType]:
        """Get the best provider based on routing strategy.
        
        Args:
            preferred_provider: Preferred provider type
            requires_vision: Whether the request requires vision support
            requires_function_calling: Whether the request requires function calling
            
        Returns:
            Selected provider type or None
        """
        available_providers = self._get_available_providers()
        
        if not available_providers:
            return None
        
        # If preferred provider is available, use it
        if preferred_provider and preferred_provider in available_providers:
            provider_reg = self._providers[preferred_provider]
            if self._check_provider_capabilities(provider_reg, requires_vision, requires_function_calling):
                return preferred_provider
        
        # Filter by capabilities
        capable_providers = [
            p for p in available_providers
            if self._check_provider_capabilities(
                self._providers[p],
                requires_vision,
                requires_function_calling
            )
        ]
        
        if not capable_providers:
            # Fall back to any available provider
            capable_providers = available_providers
        
        # Select based on routing strategy
        if self.config.routing_strategy == RoutingStrategy.PRIORITY:
            # Use the first in fallback order that is capable
            for p in self._fallback_order:
                if p in capable_providers:
                    return p
        
        elif self.config.routing_strategy == RoutingStrategy.LATENCY:
            # Use the provider with lowest latency
            return min(
                capable_providers,
                key=lambda p: self._providers[p].provider.health.latency_p50 or float('inf')
            )
        
        elif self.config.routing_strategy == RoutingStrategy.ROUND_ROBIN:
            # Round robin among capable providers
            for _ in range(len(capable_providers)):
                idx = self._round_robin_index.get(capable_providers[0], 0)
                provider = capable_providers[idx % len(capable_providers)]
                self._round_robin_index[capable_providers[0]] = idx + 1
                return provider
        
        elif self.config.routing_strategy == RoutingStrategy.COST:
            # Use the provider with lowest cost (simplified)
            return capable_providers[0]
        
        else:  # RANDOM or default
            import random
            return random.choice(capable_providers)
    
    def _check_provider_capabilities(
        self,
        registration: ProviderRegistration,
        requires_vision: bool,
        requires_function_calling: bool,
    ) -> bool:
        """Check if a provider supports required capabilities."""
        if requires_vision:
            models = registration.provider.get_available_models()
            if not any(m.supports_vision for m in models):
                return False
        
        if requires_function_calling:
            models = registration.provider.get_available_models()
            if not any(m.supports_function_calling for m in models):
                return False
        
        return True
    
    def _get_available_providers(self) -> List[ProviderType]:
        """Get list of currently available providers."""
        available = []
        for provider_type, registration in self._providers.items():
            if self.config.enable_circuit_breaker:
                if not registration.circuit_breaker.can_execute():
                    continue
            
            if registration.provider.is_available:
                available.append(provider_type)
        
        return available
    
    async def _execute_with_fallback(
        self,
        func: Callable,
        *args,
        preferred_provider: Optional[ProviderType] = None,
        requires_vision: bool = False,
        requires_function_calling: bool = False,
        **kwargs
    ) -> Any:
        """Execute a function with automatic fallback.
        
        Args:
            func: Function to execute
            *args: Positional arguments
            preferred_provider: Preferred provider type
            requires_vision: Whether vision is required
            requires_function_calling: Whether function calling is required
            **kwargs: Keyword arguments
            
        Returns:
            Result from successful provider
            
        Raises:
            AllProvidersFailedError if all providers fail
        """
        errors: List[AIProviderError] = []
        attempted_providers: List[ProviderType] = []
        
        # Determine provider order
        if preferred_provider and preferred_provider in self._providers:
            provider_order = [preferred_provider] + [
                p for p in self._fallback_order if p != preferred_provider
            ]
        else:
            provider_order = self._fallback_order
        
        for provider_type in provider_order:
            if provider_type not in self._providers:
                continue
            
            registration = self._providers[provider_type]
            
            # Skip if circuit breaker is open
            if self.config.enable_circuit_breaker:
                if not registration.circuit_breaker.can_execute():
                    continue
            
            # Check capabilities
            if not self._check_provider_capabilities(
                registration, requires_vision, requires_function_calling
            ):
                continue
            
            attempted_providers.append(provider_type)
            registration.circuit_breaker.on_execute()
            
            try:
                result = await func(registration.provider, *args, **kwargs)
                
                # Record success
                registration.circuit_breaker.record_success()
                registration.request_count += 1
                registration.last_used = datetime.utcnow()
                
                return result
                
            except RateLimitError as e:
                # Record rate limit, don't count against circuit breaker
                errors.append(e)
                self.logger.warning(
                    f"Rate limited by {provider_type.value}",
                    provider=provider_type.value
                )
                continue
                
            except (AuthenticationError, AIProviderError) as e:
                # Record failure for circuit breaker
                registration.circuit_breaker.record_failure()
                errors.append(e)
                self.logger.error(
                    f"Provider {provider_type.value} failed: {e.message}",
                    provider=provider_type.value
                )
                continue
        
        # All providers failed
        raise AllProvidersFailedError(errors)
    
    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        provider: Optional[ProviderType] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
        functions: Optional[List[FunctionDefinition]] = None,
        requires_vision: bool = False,
        **kwargs
    ) -> ChatCompletionResponse:
        """Send a chat completion request with automatic fallback.
        
        Args:
            messages: List of conversation messages
            model: Optional specific model to use
            provider: Preferred provider type
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            stop: Stop sequences
            functions: Available functions for tool use
            requires_vision: Whether vision is required
            **kwargs: Additional provider-specific arguments
            
        Returns:
            Chat completion response
        """
        requires_function_calling = functions is not None and len(functions) > 0
        
        async def execute_chat(p: BaseAIProvider) -> ChatCompletionResponse:
            return await p.chat(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                stop=stop,
                functions=functions,
                **kwargs
            )
        
        try:
            return await self._execute_with_fallback(
                execute_chat,
                preferred_provider=provider,
                requires_vision=requires_vision,
                requires_function_calling=requires_function_calling,
            )
        except AllProvidersFailedError:
            self.logger.critical(
                f"All {len(self._fallback_order)} providers failed",
                attempted_providers=[p.value for p in self._fallback_order]
            )
            raise
    
    async def stream(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        provider: Optional[ProviderType] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> StreamingResponse:
        """Send a streaming chat completion request.
        
        Note: Streaming does not support automatic fallback as it would
        result in mixed responses. Use the non-streaming chat() for fallback.
        
        Args:
            messages: List of conversation messages
            model: Optional specific model to use
            provider: Preferred provider type
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            stop: Stop sequences
            **kwargs: Additional provider-specific arguments
            
        Yields:
            Streaming chunks
        """
        provider_type = provider or self._default_provider
        
        if not provider_type or provider_type not in self._providers:
            raise AIProviderError("No available provider for streaming request")
        
        registration = self._providers[provider_type]
        
        async for chunk in registration.provider.stream(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            stop=stop,
            **kwargs
        ):
            yield chunk
    
    async def health_check_all(self) -> Dict[ProviderType, bool]:
        """Check health of all registered providers.
        
        Returns:
            Dictionary mapping provider type to health status
        """
        results = {}
        
        for provider_type, registration in self._providers.items():
            try:
                is_healthy = await registration.provider.health_check()
                results[provider_type] = is_healthy
            except Exception as e:
                self.logger.error(
                    f"Health check failed for {provider_type.value}: {e}",
                    provider=provider_type.value
                )
                results[provider_type] = False
        
        return results
    
    def get_provider_health(self) -> Dict[ProviderType, ProviderHealth]:
        """Get health status of all providers.
        
        Returns:
            Dictionary mapping provider type to health info
        """
        return {
            provider_type: reg.provider.health
            for provider_type, reg in self._providers.items()
        }
    
    def get_available_models(
        self,
        provider: Optional[ProviderType] = None
    ) -> Dict[ProviderType, List[ModelInfo]]:
        """Get available models from providers.
        
        Args:
            provider: Optional specific provider
            
        Returns:
            Dictionary mapping provider type to list of models
        """
        if provider:
            if provider in self._providers:
                return {provider: self._providers[provider].provider.get_available_models()}
            return {}
        
        return {
            provider_type: reg.provider.get_available_models()
            for provider_type, reg in self._providers.items()
        }
    
    def remove_provider(self, provider_type: ProviderType) -> bool:
        """Remove a provider from the manager.
        
        Args:
            provider_type: Provider type to remove
            
        Returns:
            True if provider was removed, False if not found
        """
        if provider_type in self._providers:
            del self._providers[provider_type]
            if self._default_provider == provider_type:
                self._default_provider = next(iter(self._providers), None)
            self._update_fallback_order()
            return True
        return False
    
    async def close_all(self) -> None:
        """Close all provider connections."""
        for registration in self._providers.values():
            await registration.provider.close()


# Factory function for creating provider instances
def create_provider(config: ProviderConfig) -> BaseAIProvider:
    """Create a provider instance from configuration.
    
    Args:
        config: Provider configuration
        
    Returns:
        Provider instance
        
    Raises:
        ValueError: If provider type is not supported
    """
    provider_type = config.provider_type
    
    # Import all provider classes to ensure registration
    from services.ai_provider import (
        gemini, openai, claude, ollama, qwen, llama, gemma, mistral
    )
    
    if provider_type not in ProviderManager.PROVIDER_CLASSES:
        raise ValueError(f"Unsupported provider type: {provider_type.value}")
    
    provider_class = ProviderManager.PROVIDER_CLASSES[provider_type]
    return provider_class(config)


# Decorator for registering provider classes
def register_provider(provider_type: ProviderType):
    """Register a provider class with the manager.
    
    Args:
        provider_type: The provider type this class handles
        
    Returns:
        Decorator function
    """
    def decorator(provider_class):
        ProviderManager.PROVIDER_CLASSES[provider_type] = provider_class
        return provider_class
    return decorator