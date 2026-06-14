"""AI Provider Package.

A comprehensive provider abstraction system for AI services with support for:
- Multiple providers: Gemini, OpenAI, Claude, Ollama, Qwen, Llama, Gemma, Mistral
- Automatic fallback when providers fail
- Retry logic with exponential backoff
- Timeout handling
- Provider routing and health monitoring
- Environment variable configuration
- Comprehensive logging

Usage:
    # Initialize from environment variables
    from services.ai_provider import AIService, load_providers_from_env
    
    service = AIService.initialize(from_env=True)
    
    # Simple chat
    response = await service.chat_simple("Hello!")
    
    # With conversation
    conversation = service.create_conversation("You are a helpful assistant")
    conversation.add_user_message("What is 2+2?")
    result = await service.chat(conversation)
    print(result.content)
    
    # Streaming
    async for chunk in service.stream(messages, temperature=0.7):
        print(chunk.delta, end="", flush=True)
"""

# Core interfaces
from services.ai_provider.base import (
    # Enums
    ProviderType,
    MessageRole,
    ProviderStatus,
    ContentType,
    # Models
    Message,
    ContentBlock,
    FunctionDefinition,
    FunctionCall,
    FunctionCallResult,
    ChatCompletionResponse,
    StreamingChunk,
    ProviderConfig,
    ProviderHealth,
    ModelInfo,
    TokenUsage,
    LatencyMetrics,
    RequestMetadata,
    # Base class
    BaseAIProvider,
    # Exceptions
    AIProviderError,
    AuthenticationError,
    RateLimitError,
    ModelNotFoundError,
    InvalidRequestError,
    ProviderUnavailableError,
    AllProvidersFailedError,
    TimeoutError,
    ContentFilteredError,
)

# Utilities
from services.ai_provider.utils import (
    RetryConfig,
    RetryState,
    retry_async,
    retry_decorator,
    CircuitBreaker,
    calculate_delay,
)

from services.ai_provider.logging_config import (
    AIProviderLogger,
    get_logger,
    set_logger,
    ProviderCallLog,
    TokenUsageLog,
)

from services.ai_provider.http_client import (
    HTTPClient,
    RateLimiter,
    estimate_token_count,
)

# Provider implementations
from services.ai_provider.gemini import GeminiProvider
from services.ai_provider.openai import OpenAIProvider
from services.ai_provider.claude import ClaudeProvider
from services.ai_provider.ollama import OllamaProvider
from services.ai_provider.qwen import QwenProvider
from services.ai_provider.llama import LlamaProvider
from services.ai_provider.gemma import GemmaProvider
from services.ai_provider.mistral import MistralProvider

# Manager and configuration
from services.ai_provider.manager import (
    ProviderManager,
    ProviderManagerConfig,
    ProviderRegistration,
    RoutingStrategy,
    create_provider,
    register_provider,
)

from services.ai_provider.config import (
    EnvConfigLoader,
    ProviderEnvConfig,
    load_providers_from_env,
    get_provider_config,
    print_env_docs,
)

# High-level service
from services.ai_provider.service import (
    AIService,
    AIServiceError,
    AIServiceNotInitializedError,
    InvalidConversationError,
    ChatOptions,
    ChatResult,
    Conversation,
    ConversationMessage,
    initialize,
    get_service,
    require_ai_service,
)


__all__ = [
    # Enums
    "ProviderType",
    "MessageRole",
    "ProviderStatus",
    "ContentType",
    "RoutingStrategy",
    # Models
    "Message",
    "ContentBlock",
    "FunctionDefinition",
    "FunctionCall",
    "FunctionCallResult",
    "ChatCompletionResponse",
    "StreamingChunk",
    "ProviderConfig",
    "ProviderHealth",
    "ModelInfo",
    "TokenUsage",
    "LatencyMetrics",
    "RequestMetadata",
    # Base
    "BaseAIProvider",
    # Exceptions
    "AIProviderError",
    "AuthenticationError",
    "RateLimitError",
    "ModelNotFoundError",
    "InvalidRequestError",
    "ProviderUnavailableError",
    "AllProvidersFailedError",
    "TimeoutError",
    "ContentFilteredError",
    # Utilities
    "RetryConfig",
    "RetryState",
    "retry_async",
    "retry_decorator",
    "CircuitBreaker",
    "calculate_delay",
    "AIProviderLogger",
    "get_logger",
    "set_logger",
    "ProviderCallLog",
    "TokenUsageLog",
    "HTTPClient",
    "RateLimiter",
    "estimate_token_count",
    # Providers
    "GeminiProvider",
    "OpenAIProvider",
    "ClaudeProvider",
    "OllamaProvider",
    "QwenProvider",
    "LlamaProvider",
    "GemmaProvider",
    "MistralProvider",
    # Manager
    "ProviderManager",
    "ProviderManagerConfig",
    "ProviderRegistration",
    "create_provider",
    "register_provider",
    # Config
    "EnvConfigLoader",
    "ProviderEnvConfig",
    "load_providers_from_env",
    "get_provider_config",
    "print_env_docs",
    # Service
    "AIService",
    "AIServiceError",
    "AIServiceNotInitializedError",
    "InvalidConversationError",
    "ChatOptions",
    "ChatResult",
    "Conversation",
    "ConversationMessage",
    "initialize",
    "get_service",
    "require_ai_service",
]

__version__ = "1.0.0"