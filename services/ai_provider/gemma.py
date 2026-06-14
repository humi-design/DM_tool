"""Google Gemma provider implementation."""

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
)
from services.ai_provider.http_client import HTTPClient
from services.ai_provider.logging_config import log_provider_call


GEMMA_MODELS = [
    ModelInfo(
        id="gemma-2-27b-it",
        name="Gemma 2 27B",
        provider=ProviderType.GEMMA,
        supports_function_calling=True,
        context_window=8192,
    ),
    ModelInfo(
        id="gemma-2-9b-it",
        name="Gemma 2 9B",
        provider=ProviderType.GEMMA,
        supports_function_calling=True,
        context_window=8192,
    ),
    ModelInfo(
        id="gemma-2-2b-it",
        name="Gemma 2 2B",
        provider=ProviderType.GEMMA,
        supports_function_calling=True,
        context_window=8192,
    ),
    ModelInfo(
        id="gemma-1.5-pro",
        name="Gemma 1.5 Pro",
        provider=ProviderType.GEMMA,
        supports_function_calling=True,
        supports_vision=True,
        context_window=8192,
    ),
    ModelInfo(
        id="gemma-1.5-flash",
        name="Gemma 1.5 Flash",
        provider=ProviderType.GEMMA,
        supports_function_calling=True,
        supports_vision=True,
        context_window=8192,
    ),
]


class GemmaProvider(BaseAIProvider):
    """Google Gemma AI provider (via Vertex AI or other APIs)."""
    
    BASE_URL = "https://api.together.xyz/v1"  # Can be configured for Vertex AI
    
    def __init__(self, config: ProviderConfig):
        self._provider_type = ProviderType.GEMMA
        super().__init__(config)
    
    @property
    def provider_type(self) -> ProviderType:
        return self._provider_type
    
    def _initialize_client(self) -> None:
        """Initialize the HTTP client for Gemma."""
        headers = {
            "Content-Type": "application/json",
        }
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        
        self._client = HTTPClient(
            base_url=self.config.base_url or self.BASE_URL,
            api_key=self.config.api_key,
            timeout=self.config.timeout,
            headers=headers,
            custom_headers=self.config.custom_headers,
        )
        self._client.provider_type = "gemma"
    
    def get_available_models(self) -> List[ModelInfo]:
        """Return available Gemma models."""
        return GEMMA_MODELS
    
    def validate_config(self) -> bool:
        """Validate Gemma configuration."""
        return self.config.api_key is not None
    
    async def health_check(self) -> bool:
        """Check if Gemma API is accessible."""
        try:
            await self._client.get("/models")
            self._health.status = ProviderStatus.AVAILABLE
            return True
        except Exception:
            self._health.status = ProviderStatus.UNAVAILABLE
            return False
    
    @log_provider_call("chat", "gemma", "model")
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
        """Send a chat completion request to Gemma."""
        model = model or self.config.model or "gemma-2-9b-it"
        start_time = datetime.utcnow()
        
        payload: Dict[str, Any] = {
            "model": model,
            "messages": [self._convert_message(m) for m in messages],
            "temperature": temperature,
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if stop:
            payload["stop"] = stop
        if functions:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": f.name,
                        "description": f.description or "",
                        "parameters": f.parameters or {"type": "object", "properties": {}},
                    }
                }
                for f in functions
            ]
        
        response = await self._client.post("/chat/completions", json=payload)
        
        choice = response["choices"][0]
        content = choice.get("message", {}).get("content", "")
        finish_reason = choice.get("finish_reason", "stop")
        
        function_call = None
        if "function_call" in choice.get("message", {}):
            fc = choice["message"]["function_call"]
            function_call = FunctionCall(
                name=fc["name"],
                arguments=fc["arguments"],
            )
            content = f"[Function call: {fc['name']}]"
        
        usage = self._extract_usage(response.get("usage", {}), model)
        latency = LatencyMetrics(
            total_time=(datetime.utcnow() - start_time).total_seconds(),
        )
        
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
            function_call=function_call,
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
        """Send a streaming chat completion request to Gemma."""
        model = model or self.config.model or "gemma-2-9b-it"
        
        payload: Dict[str, Any] = {
            "model": model,
            "messages": [self._convert_message(m) for m in messages],
            "temperature": temperature,
            "stream": True,
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if stop:
            payload["stop"] = stop
        
        full_content = ""
        finish_reason = None
        
        async for line in self._client.stream_post("/chat/completions", json=payload):
            if line.startswith("data:"):
                if line.strip() == "data: [DONE]":
                    break
                
                data = json.loads(line[5:])
                delta = data["choices"][0].get("delta", {})
                
                if "content" in delta:
                    token = delta["content"]
                    full_content += token
                    yield StreamingChunk(
                        content=full_content,
                        delta=token,
                        is_final=False,
                    )
                
                if "finish_reason" in data["choices"][0]:
                    finish_reason = data["choices"][0]["finish_reason"]
        
        yield StreamingChunk(
            content=full_content,
            delta="",
            is_final=True,
            finish_reason=finish_reason,
        )
    
    def _convert_message(self, message: Message) -> Dict[str, Any]:
        """Convert Message to API format."""
        msg = {
            "role": message.role.value,
        }
        
        if isinstance(message.content, str):
            msg["content"] = message.content
        else:
            content_parts = []
            for block in message.content:
                if block.type.value == "text":
                    content_parts.append({
                        "type": "text",
                        "text": block.text,
                    })
                elif block.type.value == "image":
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {"url": block.image_url},
                    })
            msg["content"] = content_parts
        
        return msg
    
    def _extract_usage(
        self,
        usage_data: Dict[str, Any],
        model: str
    ) -> TokenUsage:
        """Extract token usage from response."""
        prompt_tokens = usage_data.get("prompt_tokens", 0)
        completion_tokens = usage_data.get("completion_tokens", 0)
        total_tokens = usage_data.get("total_tokens", 0)
        
        # Gemma is generally free on Vertex AI, so cost is 0
        return TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=0.0,
        )
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.close()