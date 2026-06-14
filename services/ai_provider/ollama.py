"""Ollama provider implementation for local models."""

import json
from typing import Optional, List, Dict, Any, AsyncIterator
from datetime import datetime

from services.ai_provider.base import (
    BaseAIProvider,
    ProviderType,
    ProviderConfig,
    Message,
    FunctionDefinition,
    FunctionCall,
    ChatCompletionResponse,
    StreamingChunk,
    TokenUsage,
    LatencyMetrics,
    RequestMetadata,
    ModelInfo,
    ProviderStatus,
    ContentBlock,
)
from services.ai_provider.http_client import HTTPClient
from services.ai_provider.logging_config import log_provider_call


# Default Ollama models - users can configure their own
OLLAMA_MODELS = [
    ModelInfo(
        id="llama3.2",
        name="Llama 3.2",
        provider=ProviderType.OLLAMA,
        supports_function_calling=False,
        context_window=128000,
    ),
    ModelInfo(
        id="llama3.1",
        name="Llama 3.1",
        provider=ProviderType.OLLAMA,
        supports_function_calling=False,
        context_window=128000,
    ),
    ModelInfo(
        id="llama3",
        name="Llama 3",
        provider=ProviderType.OLLAMA,
        supports_function_calling=False,
        context_window=128000,
    ),
    ModelInfo(
        id="llama2",
        name="Llama 2",
        provider=ProviderType.OLLAMA,
        supports_function_calling=False,
        context_window=4096,
    ),
    ModelInfo(
        id="mistral",
        name="Mistral",
        provider=ProviderType.OLLAMA,
        supports_function_calling=False,
        context_window=8192,
    ),
    ModelInfo(
        id="mixtral",
        name="Mixtral",
        provider=ProviderType.OLLAMA,
        supports_function_calling=False,
        context_window=32768,
    ),
    ModelInfo(
        id="codellama",
        name="Code Llama",
        provider=ProviderType.OLLAMA,
        supports_function_calling=False,
        context_window=16384,
    ),
    ModelInfo(
        id="phi3",
        name="Phi-3",
        provider=ProviderType.OLLAMA,
        supports_function_calling=False,
        context_window=4096,
    ),
    ModelInfo(
        id="gemma2",
        name="Gemma 2",
        provider=ProviderType.OLLAMA,
        supports_function_calling=False,
        context_window=8192,
    ),
    ModelInfo(
        id="qwen2.5",
        name="Qwen 2.5",
        provider=ProviderType.OLLAMA,
        supports_function_calling=False,
        context_window=32768,
    ),
    ModelInfo(
        id="nomic-embed-text",
        name="Nomic Embed Text",
        provider=ProviderType.OLLAMA,
        supports_function_calling=False,
        context_window=8192,
    ),
]


class OllamaProvider(BaseAIProvider):
    """Ollama local model provider."""
    
    BASE_URL = "http://localhost:11434"
    
    def __init__(self, config: ProviderConfig):
        self._provider_type = ProviderType.OLLAMA
        self._models_cache: Optional[List[ModelInfo]] = None
        super().__init__(config)
    
    @property
    def provider_type(self) -> ProviderType:
        return self._provider_type
    
    def _initialize_client(self) -> None:
        """Initialize the HTTP client for Ollama."""
        self._client = HTTPClient(
            base_url=self.config.base_url or self.BASE_URL,
            timeout=self.config.timeout,
            custom_headers=self.config.custom_headers,
        )
        self._client.provider_type = "ollama"
    
    def get_available_models(self) -> List[ModelInfo]:
        """Return available Ollama models."""
        if self._models_cache is not None:
            return self._models_cache
        
        return OLLAMA_MODELS
    
    async def fetch_available_models(self) -> List[ModelInfo]:
        """Fetch models from the Ollama API."""
        try:
            response = await self._client.get("/api/tags")
            models = response.get("models", [])
            
            self._models_cache = [
                ModelInfo(
                    id=m["name"],
                    name=m["name"],
                    provider=ProviderType.OLLAMA,
                    supports_function_calling=False,
                    context_window=m.get("details", {}).get("context_length"),
                )
                for m in models
            ]
            return self._models_cache
        except Exception:
            return OLLAMA_MODELS
    
    def validate_config(self) -> bool:
        """Validate Ollama configuration."""
        # Ollama doesn't require API key for local usage
        return True
    
    async def health_check(self) -> bool:
        """Check if Ollama server is accessible."""
        try:
            response = await self._client.get("/")
            if response.get("version"):
                self._health.status = ProviderStatus.AVAILABLE
                return True
        except Exception:
            self._health.status = ProviderStatus.UNAVAILABLE
        return False
    
    @log_provider_call("chat", "ollama", "model")
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
        """Send a chat completion request to Ollama."""
        model = model or self.config.model or "llama3.2"
        start_time = datetime.utcnow()
        
        # Build request payload
        payload: Dict[str, Any] = {
            "model": model,
            "messages": [self._convert_message(m) for m in messages],
            "stream": False,
        }
        
        if temperature:
            payload["options"]["temperature"] = temperature
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        if stop:
            payload["options"]["stop"] = stop
        
        # Make request
        response = await self._client.post("/api/chat", json=payload)
        
        # Parse response
        message = response.get("message", {})
        content = message.get("content", "")
        finish_reason = "stop"
        
        if response.get("done"):
            finish_reason = response.get("done_reason", "stop")
        
        # Extract usage (Ollama provides limited usage info)
        usage = self._extract_usage(response.get("prompt_eval_count", 0), response.get("eval_count", 0))
        
        # Calculate latency
        latency = LatencyMetrics(
            total_time=(datetime.utcnow() - start_time).total_seconds(),
        )
        
        # Update health
        self.update_health(True, latency.total_time or 0)
        
        return ChatCompletionResponse(
            content=content,
            model=model,
            provider=self.provider_type,
            finish_reason=finish_reason,
            usage=usage,
            latency=latency,
            metadata=RequestMetadata(
                model=model,
                provider=self.provider_type,
                timestamp=start_time,
            ),
            raw_response=response,
        )
    
    async def stream(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> AsyncIterator[StreamingChunk]:
        """Send a streaming chat completion request to Ollama."""
        model = model or self.config.model or "llama3.2"
        
        payload: Dict[str, Any] = {
            "model": model,
            "messages": [self._convert_message(m) for m in messages],
            "stream": True,
        }
        
        if temperature:
            payload["options"]["temperature"] = temperature
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        if stop:
            payload["options"]["stop"] = stop
        
        full_content = ""
        finish_reason = None
        
        async for line in self._client.stream_post("/api/chat", json=payload):
            if line.startswith("{"):
                data = json.loads(line)
                message = data.get("message", {})
                
                if "content" in message:
                    token = message["content"]
                    full_content += token
                    yield StreamingChunk(
                        content=full_content,
                        delta=token,
                        is_final=False,
                    )
                
                if data.get("done"):
                    finish_reason = data.get("done_reason", "stop")
        
        yield StreamingChunk(
            content=full_content,
            delta="",
            is_final=True,
            finish_reason=finish_reason,
        )
    
    def _convert_message(self, message: Message) -> Dict[str, Any]:
        """Convert Message to Ollama format."""
        msg = {
            "role": message.role.value,
            "content": message.content if isinstance(message.content, str) else "",
        }
        return msg
    
    def _extract_usage(
        self,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> TokenUsage:
        """Extract token usage from response."""
        # Ollama provides prompt_eval_count and eval_count
        return TokenUsage(
            prompt_tokens=prompt_tokens or 0,
            completion_tokens=completion_tokens or 0,
            total_tokens=(prompt_tokens or 0) + (completion_tokens or 0),
            cost=0.0,  # Local models have no API cost
        )
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.close()