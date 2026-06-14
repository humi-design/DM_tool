"""Services package for business logic layer."""

from services.auth_service import (
    AuthService,
    AuthError,
    AuthResult,
    InvalidCredentialsError,
    RateLimitError,
    AccountLockedError,
    GoogleOAuthService,
)

# AI Provider module
from services.ai_provider import (
    AIService,
    AIServiceError,
    AIServiceNotInitializedError,
    InvalidConversationError,
    ChatOptions,
    ChatResult,
    Conversation,
    ConversationMessage,
    ProviderManager,
    ProviderManagerConfig,
    ProviderType,
    Message,
    MessageRole,
    BaseAIProvider,
    ProviderConfig,
    load_providers_from_env,
    initialize,
    get_service,
)

__all__ = [
    # Auth
    "AuthService",
    "AuthError",
    "AuthResult",
    "InvalidCredentialsError",
    "RateLimitError",
    "AccountLockedError",
    "GoogleOAuthService",
    # AI Provider
    "AIService",
    "AIServiceError",
    "AIServiceNotInitializedError",
    "InvalidConversationError",
    "ChatOptions",
    "ChatResult",
    "Conversation",
    "ConversationMessage",
    "ProviderManager",
    "ProviderManagerConfig",
    "ProviderType",
    "Message",
    "MessageRole",
    "BaseAIProvider",
    "ProviderConfig",
    "load_providers_from_env",
    "initialize",
    "get_service",
]