"""AIService - High-level abstraction for AI operations."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Union, AsyncIterator, TypeVar, Generic
from enum import Enum

from services.ai_provider.base import (
    ProviderType,
    ProviderConfig,
    Message,
    MessageRole,
    FunctionDefinition,
    FunctionCall,
    ChatCompletionResponse,
    StreamingChunk,
    TokenUsage,
    ModelInfo,
    ProviderHealth,
    ContentBlock,
    ContentType,
)
from services.ai_provider.manager import (
    ProviderManager,
    ProviderManagerConfig,
    RoutingStrategy,
    create_provider,
)
from services.ai_provider.logging_config import AIProviderLogger, get_logger


T = TypeVar('T')


class AIServiceError(Exception):
    """Base exception for AIService errors."""
    pass


class AIServiceNotInitializedError(AIServiceError):
    """Raised when AIService is not initialized."""
    pass


class InvalidConversationError(AIServiceError):
    """Raised when conversation format is invalid."""
    pass


class ConversationMessage:
    """A message in a conversation with convenient helpers."""
    
    def __init__(
        self,
        role: Union[MessageRole, str],
        content: Union[str, List[ContentBlock]],
        name: Optional[str] = None,
    ):
        if isinstance(role, str):
            role = MessageRole(role)
        self.role = role
        self.content = content
        self.name = name
    
    def to_message(self) -> Message:
        """Convert to base Message object."""
        return Message(
            role=self.role,
            content=self.content,
            name=self.name,
        )
    
    @classmethod
    def system(cls, content: str) -> 'ConversationMessage':
        """Create a system message."""
        return cls(MessageRole.SYSTEM, content)
    
    @classmethod
    def user(cls, content: str) -> 'ConversationMessage':
        """Create a user message."""
        return cls(MessageRole.USER, content)
    
    @classmethod
    def assistant(cls, content: str) -> 'ConversationMessage':
        """Create an assistant message."""
        return cls(MessageRole.ASSISTANT, content)
    
    @classmethod
    def from_message(cls, message: Message) -> 'ConversationMessage':
        """Create from a Message object."""
        return cls(message.role, message.content, message.name)


@dataclass
class ChatOptions:
    """Options for chat completion."""
    model: Optional[str] = None
    provider: Optional[ProviderType] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stop: Optional[List[str]] = None
    functions: Optional[List[FunctionDefinition]] = None
    requires_vision: bool = False


@dataclass
class ChatResult:
    """Result from a chat completion."""
    content: str
    model: str
    provider: ProviderType
    finish_reason: Optional[str] = None
    usage: TokenUsage = field(default_factory=TokenUsage)
    function_call: Optional[FunctionCall] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class Conversation:
    """Manages a conversation with AI.
    
    Provides a high-level interface for maintaining conversation history
    and sending messages to AI providers.
    """
    
    def __init__(
        self,
        system_prompt: Optional[str] = None,
        messages: Optional[List[ConversationMessage]] = None,
    ):
        """Initialize a conversation.
        
        Args:
            system_prompt: Optional system prompt
            messages: Optional initial messages
        """
        self.messages: List[ConversationMessage] = []
        
        if system_prompt:
            self.messages.append(ConversationMessage.system(system_prompt))
        
        if messages:
            self.messages.extend(messages)
    
    def add_message(
        self,
        role: Union[MessageRole, str],
        content: str,
    ) -> 'Conversation':
        """Add a message to the conversation.
        
        Args:
            role: Message role
            content: Message content
            
        Returns:
            Self for chaining
        """
        self.messages.append(ConversationMessage(role, content))
        return self
    
    def add_user_message(self, content: str) -> 'Conversation':
        """Add a user message."""
        return self.add_message(MessageRole.USER, content)
    
    def add_assistant_message(self, content: str) -> 'Conversation':
        """Add an assistant message."""
        return self.add_message(MessageRole.ASSISTANT, content)
    
    def add_system_message(self, content: str) -> 'Conversation':
        """Add a system message."""
        return self.add_message(MessageRole.SYSTEM, content)
    
    def add_function_result(
        self,
        call_id: str,
        output: str,
        error: Optional[str] = None,
    ) -> 'Conversation':
        """Add a function call result as a tool message."""
        content = output if not error else f"Error: {error}"
        msg = ConversationMessage(
            MessageRole.TOOL,
            content,
        )
        msg.tool_call_id = call_id
        self.messages.append(msg)
        return self
    
    def get_messages(self) -> List[Message]:
        """Get all messages as base Message objects."""
        return [m.to_message() for m in self.messages]
    
    def clear(self, keep_system: bool = True) -> 'Conversation':
        """Clear conversation history.
        
        Args:
            keep_system: Whether to keep the system prompt
            
        Returns:
            Self for chaining
        """
        if keep_system:
            self.messages = [m for m in self.messages if m.role == MessageRole.SYSTEM]
        else:
            self.messages = []
        return self
    
    def __len__(self) -> int:
        """Get number of messages."""
        return len(self.messages)
    
    def __repr__(self) -> str:
        return f"Conversation({len(self.messages)} messages)"


class AIService:
    """High-level service for AI interactions.
    
    This is the main entry point for using the AI provider system.
    It provides a simple, high-level interface while supporting
    all the advanced features like fallback, retry, and routing.
    """
    
    _instance: Optional['AIService'] = None
    
    def __init__(
        self,
        manager: Optional[ProviderManager] = None,
        logger: Optional[AIProviderLogger] = None,
    ):
        """Initialize the AI service.
        
        Args:
            manager: Optional ProviderManager instance
            logger: Optional logger instance
        """
        self._manager = manager
        self._logger = logger or get_logger()
        self._initialized = False
    
    @classmethod
    def get_instance(cls) -> 'AIService':
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = AIService()
        return cls._instance
    
    @classmethod
    def initialize(
        cls,
        manager: Optional[ProviderManager] = None,
        from_env: bool = True,
        **kwargs
    ) -> 'AIService':
        """Initialize the AI service.
        
        Args:
            manager: Optional ProviderManager instance
            from_env: Whether to load providers from environment
            **kwargs: Additional arguments for manager config
            
        Returns:
            Initialized AIService instance
        """
        instance = cls.get_instance()
        
        if manager:
            instance._manager = manager
        elif from_env:
            instance._manager = load_providers_from_env()
        
        if instance._manager is None:
            config = ProviderManagerConfig(**kwargs)
            instance._manager = ProviderManager(config)
        
        instance._initialized = True
        return instance
    
    @property
    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._initialized and self._manager is not None
    
    def _ensure_initialized(self) -> None:
        """Ensure service is initialized."""
        if not self.is_initialized:
            raise AIServiceNotInitializedError(
                "AIService not initialized. Call AIService.initialize() first."
            )
    
    async def chat(
        self,
        messages: Union[List[Message], List[ConversationMessage], Conversation],
        options: Optional[ChatOptions] = None,
        **kwargs
    ) -> ChatResult:
        """Send a chat completion request.
        
        Args:
            messages: Messages to send (various formats supported)
            options: Optional chat options
            **kwargs: Additional options (overrides ChatOptions)
            
        Returns:
            ChatResult with the response
        """
        self._ensure_initialized()
        
        # Convert messages to base format
        if isinstance(messages, Conversation):
            base_messages = messages.get_messages()
        elif all(isinstance(m, ConversationMessage) for m in messages):
            base_messages = [m.to_message() for m in messages]
        else:
            base_messages = messages
        
        # Merge options with kwargs
        if options:
            kwargs.setdefault('model', options.model)
            kwargs.setdefault('provider', options.provider)
            kwargs.setdefault('temperature', options.temperature)
            kwargs.setdefault('max_tokens', options.max_tokens)
            kwargs.setdefault('stop', options.stop)
            kwargs.setdefault('functions', options.functions)
            kwargs.setdefault('requires_vision', options.requires_vision)
        
        # Make request
        response = await self._manager.chat(
            messages=base_messages,
            **kwargs
        )
        
        return ChatResult(
            content=response.content,
            model=response.model,
            provider=response.provider,
            finish_reason=response.finish_reason,
            usage=response.usage,
            function_call=response.function_call,
            metadata={
                'request_id': response.metadata.request_id,
                'latency': response.latency,
            },
        )
    
    async def chat_simple(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """Simple chat with a single prompt.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            **kwargs: Additional options
            
        Returns:
            Response content as string
        """
        messages = []
        if system_prompt:
            messages.append(Message(role=MessageRole.SYSTEM, content=system_prompt))
        messages.append(Message(role=MessageRole.USER, content=prompt))
        
        result = await self.chat(messages, **kwargs)
        return result.content
    
    async def stream(
        self,
        messages: Union[List[Message], List[ConversationMessage], Conversation],
        options: Optional[ChatOptions] = None,
        **kwargs
    ) -> AsyncIterator[StreamingChunk]:
        """Send a streaming chat request.
        
        Note: Streaming does not support automatic fallback.
        
        Args:
            messages: Messages to send
            options: Optional chat options
            **kwargs: Additional options
            
        Yields:
            Streaming chunks
        """
        self._ensure_initialized()
        
        # Convert messages
        if isinstance(messages, Conversation):
            base_messages = messages.get_messages()
        elif all(isinstance(m, ConversationMessage) for m in messages):
            base_messages = [m.to_message() for m in messages]
        else:
            base_messages = messages
        
        # Merge options
        if options:
            kwargs.setdefault('model', options.model)
            kwargs.setdefault('provider', options.provider)
            kwargs.setdefault('temperature', options.temperature)
            kwargs.setdefault('max_tokens', options.max_tokens)
            kwargs.setdefault('stop', options.stop)
        
        async for chunk in self._manager.stream(base_messages, **kwargs):
            yield chunk
    
    def create_conversation(
        self,
        system_prompt: Optional[str] = None,
    ) -> Conversation:
        """Create a new conversation.
        
        Args:
            system_prompt: Optional system prompt
            
        Returns:
            New Conversation instance
        """
        return Conversation(system_prompt=system_prompt)
    
    async def chat_with_conversation(
        self,
        conversation: Conversation,
        user_message: str,
        **kwargs
    ) -> str:
        """Add a user message and get AI response.
        
        Args:
            conversation: Conversation to use
            user_message: User message to add
            **kwargs: Additional options
            
        Returns:
            AI response content
        """
        conversation.add_user_message(user_message)
        result = await self.chat(conversation, **kwargs)
        conversation.add_assistant_message(result.content)
        return result.content
    
    def get_available_providers(self) -> List[ProviderType]:
        """Get list of available provider types."""
        self._ensure_initialized()
        return list(self._manager._providers.keys())
    
    def get_provider_health(self) -> Dict[ProviderType, ProviderHealth]:
        """Get health status of all providers."""
        self._ensure_initialized()
        return self._manager.get_provider_health()
    
    def get_available_models(
        self,
        provider: Optional[ProviderType] = None
    ) -> Dict[ProviderType, List[ModelInfo]]:
        """Get available models from providers."""
        self._ensure_initialized()
        return self._manager.get_available_models(provider)
    
    async def health_check(self) -> Dict[ProviderType, bool]:
        """Check health of all providers."""
        self._ensure_initialized()
        return await self._manager.health_check_all()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get usage metrics."""
        self._ensure_initialized()
        return self._logger.get_metrics()
    
    async def close(self) -> None:
        """Close all provider connections."""
        if self._manager:
            await self._manager.close_all()


# Convenience instance functions
_instance: Optional[AIService] = None


def initialize(**kwargs) -> AIService:
    """Initialize the global AIService instance."""
    global _instance
    _instance = AIService.initialize(**kwargs)
    return _instance


def get_service() -> AIService:
    """Get the global AIService instance."""
    global _instance
    if _instance is None:
        _instance = AIService()
    return _instance


async def chat(prompt: str, **kwargs) -> str:
    """Simple chat with a single prompt."""
    service = get_service()
    if not service.is_initialized:
        initialize()
    return await service.chat_simple(prompt, **kwargs)


# Decorator for automatic initialization
def require_ai_service(func):
    """Decorator to ensure AIService is initialized."""
    async def wrapper(*args, **kwargs):
        service = get_service()
        if not service.is_initialized:
            initialize()
        return await func(*args, **kwargs)
    return wrapper