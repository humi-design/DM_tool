"""AI Provider Base Interface and Models.

This module defines the core abstractions for AI service providers,
including the base provider interface, request/response models, and
custom exceptions.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, TypeVar, Union, List, Dict, AsyncIterator
import uuid

from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# Enums
# =============================================================================

class ProviderType(Enum):
    """Supported AI provider types."""
    GEMINI = "gemini"
    OPENAI = "openai"
    CLAUDE = "claude"
    OLLAMA = "ollama"
    QWEN = "qwen"
    LLAMA = "llama"
    GEMMA = "gemma"
    MISTRAL = "mistral"


class MessageRole(Enum):
    """Message roles in a conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ProviderStatus(Enum):
    """Provider availability status."""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"
    DEGRADED = "degraded"


class ContentType(Enum):
    """Type of content in a message."""
    TEXT = "text"
    IMAGE = "image"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"


# =============================================================================
# Request/Response Models
# =============================================================================

class ContentBlock(BaseModel):
    """Content block for messages."""
    type: ContentType
    text: Optional[str] = None
    image_url: Optional[str] = None
    tool_use: Optional[Dict[str, Any]] = None
    tool_result: Optional[Dict[str, Any]] = None


class Message(BaseModel):
    """Chat message model."""
    role: MessageRole
    content: Union[str, List[ContentBlock]]
    name: Optional[str] = None
    tool_call_id: Optional[str] = None

    model_config = ConfigDict(use_enum_values=True)


class FunctionDefinition(BaseModel):
    """Function/tool definition for function calling."""
    name: str
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class FunctionCall(BaseModel):
    """Function call from model response."""
    name: str
    arguments: str
    call_id: Optional[str] = None


class FunctionCallResult(BaseModel):
    """Result of a function call."""
    call_id: str
    output: str
    error: Optional[str] = None


@dataclass
class ModelInfo:
    """Information about an AI model."""
    id: str
    name: str
    provider: ProviderType
    supports_function_calling: bool = False
    supports_vision: bool = False
    max_tokens: Optional[int] = None
    context_window: Optional[int] = None
    cost_per_input_token: Optional[float] = None
    cost_per_output_token: Optional[float] = None


@dataclass
class TokenUsage:
    """Token usage statistics."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0


@dataclass
class LatencyMetrics:
    """Latency metrics for a request."""
    time_to_first_token: Optional[float] = None
    total_time: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RequestMetadata:
    """Metadata for a request."""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    model: Optional[str] = None
    provider: Optional[ProviderType] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    retry_count: int = 0


class ChatCompletionResponse(BaseModel):
    """Response from chat completion."""
    content: str
    model: str
    provider: ProviderType
    finish_reason: Optional[str] = None
    usage: TokenUsage = field(default_factory=TokenUsage)
    latency: Optional[LatencyMetrics] = None
    metadata: RequestMetadata = field(default_factory=RequestMetadata)
    function_call: Optional[FunctionCall] = None
    raw_response: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(use_enum_values=True)


class StreamingChunk(BaseModel):
    """Streaming response chunk."""
    content: str
    delta: str
    is_final: bool = False
    finish_reason: Optional[str] = None
    function_call: Optional[FunctionCall] = None


# Type alias for streaming responses
StreamingResponse = AsyncIterator[StreamingChunk]


# =============================================================================
# Configuration Models
# =============================================================================

class ProviderConfig(BaseModel):
    """Configuration for an AI provider."""
    provider_type: ProviderType
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    timeout: float = 60.0
    max_retries: int = 3
    retry_delay: float = 1.0
    max_backoff: float = 60.0
    enabled: bool = True
    priority: int = 0  # Lower = higher priority
    rate_limit: Optional[int] = None  # Requests per minute
    custom_headers: Dict[str, str] = Field(default_factory=dict)
    extra: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(use_enum_values=True)


class ProviderHealth(BaseModel):
    """Health status of a provider."""
    provider_type: ProviderType
    status: ProviderStatus
    latency_p50: Optional[float] = None
    latency_p95: Optional[float] = None
    latency_p99: Optional[float] = None
    error_rate: float = 0.0
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    consecutive_failures: int = 0

    model_config = ConfigDict(use_enum_values=True)


# =============================================================================
# Base Provider Interface
# =============================================================================

class BaseAIProvider(ABC):
    """Abstract base class for AI providers.
    
    All AI providers must implement this interface to ensure
    consistent behavior across different providers.
    """

    def __init__(self, config: ProviderConfig):
        """Initialize the provider with configuration.
        
        Args:
            config: Provider-specific configuration
        """
        self.config = config
        self._health = ProviderHealth(
            provider_type=config.provider_type,
            status=ProviderStatus.AVAILABLE,
        )
        self._initialize_client()

    @abstractmethod
    def _initialize_client(self) -> None:
        """Initialize the provider-specific HTTP client.
        
        This method should be implemented by each provider to set up
        their specific client configuration.
        """
        pass

    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """Return the provider type."""
        pass

    @property
    def is_available(self) -> bool:
        """Check if the provider is currently available."""
        return (
            self.config.enabled and 
            self._health.status in (ProviderStatus.AVAILABLE, ProviderStatus.DEGRADED)
        )

    @property
    def health(self) -> ProviderHealth:
        """Return the current health status."""
        return self._health

    def update_health(self, success: bool, latency: float) -> None:
        """Update health metrics based on request result.
        
        Args:
            success: Whether the request succeeded
            latency: Request latency in seconds
        """
        now = datetime.utcnow()
        
        if success:
            self._health.last_success = now
            self._health.consecutive_failures = 0
            if self._health.status == ProviderStatus.RATE_LIMITED:
                self._health.status = ProviderStatus.AVAILABLE
        else:
            self._health.last_failure = now
            self._health.consecutive_failures += 1
            
            if self._health.consecutive_failures >= 5:
                self._health.status = ProviderStatus.UNAVAILABLE
            elif self._health.consecutive_failures >= 2:
                self._health.status = ProviderStatus.DEGRADED

    @abstractmethod
    def get_available_models(self) -> List[ModelInfo]:
        """Return list of available models for this provider.
        
        Returns:
            List of ModelInfo objects
        """
        pass

    @abstractmethod
    async def chat(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
        functions: Optional[List[FunctionDefinition]] = None,
        **kwargs
    ) -> ChatCompletionResponse:
        """Send a chat completion request.
        
        Args:
            messages: List of conversation messages
            model: Model to use (provider-specific)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            stop: Stop sequences
            functions: Available functions for tool use
            
        Returns:
            ChatCompletionResponse with the model's response
        """
        pass

    @abstractmethod
    async def stream(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> AsyncIterator[StreamingChunk]:
        """Send a streaming chat completion request.
        
        Args:
            messages: List of conversation messages
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            stop: Stop sequences
            
        Yields:
            StreamingChunk for each token received
        """
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate provider configuration.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Perform a health check on the provider.
        
        Returns:
            True if provider is healthy, False otherwise
        """
        pass

    async def close(self) -> None:
        """Clean up provider resources."""
        pass


# =============================================================================
# Provider Exceptions
# =============================================================================

class AIProviderError(Exception):
    """Base exception for AI provider errors."""
    def __init__(self, message: str, provider: Optional[ProviderType] = None, details: Optional[Dict] = None):
        self.message = message
        self.provider = provider
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(AIProviderError):
    """Authentication failed with the provider."""
    pass


class RateLimitError(AIProviderError):
    """Rate limit exceeded for the provider."""
    def __init__(self, message: str, provider: Optional[ProviderType] = None, retry_after: Optional[float] = None):
        super().__init__(message, provider)
        self.retry_after = retry_after


class ModelNotFoundError(AIProviderError):
    """Requested model not found or not available."""
    pass


class InvalidRequestError(AIProviderError):
    """Invalid request parameters."""
    pass


class ProviderUnavailableError(AIProviderError):
    """Provider is currently unavailable."""
    pass


class AllProvidersFailedError(AIProviderError):
    """All providers failed to respond."""
    def __init__(self, errors: List[AIProviderError]):
        self.errors = errors
        super().__init__(
            f"All {len(errors)} providers failed. See self.errors for details.",
            details={"errors": [{"provider": e.provider, "message": e.message} for e in errors]}
        )


class TimeoutError(AIProviderError):
    """Request timed out."""
    pass


class ContentFilteredError(AIProviderError):
    """Content was filtered by the provider."""
    pass