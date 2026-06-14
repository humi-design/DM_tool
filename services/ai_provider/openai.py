"""OpenAI provider implementation."""

import json
from typing import Optional, List, Dict, Any, AsyncIterator
from datetime import datetime

from services.ai_provider.base import (
    BaseAIProvider,
    ProviderType,
    ProviderConfig,
    Message,
    MessageRole,
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


OPENAI_MODELS = [
    ModelInfo(
        id="gpt-4o",
        name="GPT-4o",
        provider=ProviderType.OPENAI,
        supports_function_calling=True,
        supports_vision=True,
        context_window=128000,
        cost_per_input_token=0.005,
        cost_per_output_token=0.015,
    ),
    ModelInfo(
        id="gpt-4o-mini",
        name="GPT-4o Mini",
        provider=ProviderType.OPENAI,
        supports_function_calling=True,
        supports_vision=True,
        context_window=128000,
        cost_per_input_token=0.00015,
        cost_per_output_token=0.0006,
    ),
    ModelInfo(
        id="gpt-4-turbo",
        name="GPT-4 Turbo",
        provider=ProviderType.OPENAI,
        supports_function_calling=True,
        supports_vision=True,
        context_window=128000,
        cost_per_input_token=0.01,
        cost_per_output_token=0.03,
    ),
    ModelInfo(
        id="gpt-4",
        name="GPT-4",
        provider=ProviderType.OPENAI,
        supports_function_calling=True,
        context_window=8192,
        cost_per_input_token=0.03,
        cost_per_output_token=0.06,
    ),
    ModelInfo(
        id="gpt-3.5-turbo",
        name="GPT-3.5 Turbo",
        provider=ProviderType.OPENAI,
        supports_function_calling=True,
        context_window=16385,
        cost_per_input_token=0.0005,
        cost_per_output_token=0.0015,
    ),
]


class OpenAIProvider(BaseAIProvider):
    """OpenAI API provider."""
    
    BASE_URL = "https://api.openai.com/v1"
    
    def __init__(self, config: ProviderConfig):
        self._provider_type = ProviderType.OPENAI
        super().__init__(config)
    
    @property
    def provider_type(self) -> ProviderType:
        return self._provider_type
    
    def _initialize_client(self) -> None:
        """Initialize the HTTP client for OpenAI."""
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
        self._client.provider_type = "openai"
    
    def get_available_models(self) -> List[ModelInfo]:
        """Return available OpenAI models."""
        return OPENAI_MODELS
    
    def validate_config(self) -> bool:
        """Validate OpenAI configuration."""
        return self.config.api_key is not None
    
    async def health_check(self) -> bool:
        """Check if OpenAI API is accessible."""
        try:
            await self._client.get("/models/gpt-4o")
            self._health.status = ProviderStatus.AVAILABLE
            return True
        except Exception:
            self._health.status = ProviderStatus.UNAVAILABLE
            return False
    
    @log_provider_call("chat", "openai", "model")
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
        """Send a chat completion request to OpenAI."""
        model = model or self.config.model or "gpt-4o"
        start_time = datetime.utcnow()
        
        # Build request payload
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
            if kwargs.get("tool_choice"):
                payload["tool_choice"] = kwargs["tool_choice"]
        
        # Make request
        response = await self._client.post("/chat/completions", json=payload)
        
        # Parse response
        choice = response["choices"][0]
        content = choice.get("message", {}).get("content", "")
        finish_reason = choice.get("finish_reason", "stop")
        
        # Handle function calls
        function_call = None
        if "function_call" in choice.get("message", {}):
            fc = choice["message"]["function_call"]
            function_call = FunctionCall(
                name=fc["name"],
                arguments=fc["arguments"],
            )
            content = f"[Function call: {fc['name']}]"
        
        # Extract usage
        usage = self._extract_usage(response.get("usage", {}), model)
        
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
        """Send a streaming chat completion request to OpenAI."""
        model = model or self.config.model or "gpt-4o"
        
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
        """Convert Message to OpenAI format."""
        msg = {
            "role": message.role.value,
        }
        
        if isinstance(message.content, str):
            msg["content"] = message.content
        else:
            # Handle content blocks
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
        
        if message.name:
            msg["name"] = message.name
        if message.tool_call_id:
            msg["tool_call_id"] = message.tool_call_id
        
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
        
        # Calculate cost
        model_info = next(
            (m for m in OPENAI_MODELS if m.id == model),
            OPENAI_MODELS[0]
        )
        cost = 0.0
        if model_info.cost_per_input_token:
            cost += (prompt_tokens / 1000) * model_info.cost_per_input_token
        if model_info.cost_per_output_token:
            cost += (completion_tokens / 1000) * model_info.cost_per_output_token
        
        return TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost,
        )
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.close()