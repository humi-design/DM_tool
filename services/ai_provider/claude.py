"""Anthropic Claude provider implementation."""

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


CLAUDE_MODELS = [
    ModelInfo(
        id="claude-opus-4-5",
        name="Claude Opus 4",
        provider=ProviderType.CLAUDE,
        supports_function_calling=True,
        supports_vision=True,
        context_window=200000,
        cost_per_input_token=0.015,
        cost_per_output_token=0.075,
    ),
    ModelInfo(
        id="claude-sonnet-4-5",
        name="Claude Sonnet 4",
        provider=ProviderType.CLAUDE,
        supports_function_calling=True,
        supports_vision=True,
        context_window=200000,
        cost_per_input_token=0.003,
        cost_per_output_token=0.015,
    ),
    ModelInfo(
        id="claude-haiku-4",
        name="Claude Haiku 4",
        provider=ProviderType.CLAUDE,
        supports_function_calling=True,
        supports_vision=True,
        context_window=200000,
        cost_per_input_token=0.0008,
        cost_per_output_token=0.004,
    ),
    ModelInfo(
        id="claude-3-opus",
        name="Claude 3 Opus",
        provider=ProviderType.CLAUDE,
        supports_function_calling=True,
        supports_vision=True,
        context_window=200000,
        cost_per_input_token=0.015,
        cost_per_output_token=0.075,
    ),
    ModelInfo(
        id="claude-3-sonnet",
        name="Claude 3 Sonnet",
        provider=ProviderType.CLAUDE,
        supports_function_calling=True,
        supports_vision=True,
        context_window=200000,
        cost_per_input_token=0.003,
        cost_per_output_token=0.015,
    ),
    ModelInfo(
        id="claude-3-haiku",
        name="Claude 3 Haiku",
        provider=ProviderType.CLAUDE,
        supports_function_calling=True,
        supports_vision=True,
        context_window=200000,
        cost_per_input_token=0.0008,
        cost_per_output_token=0.004,
    ),
]


class ClaudeProvider(BaseAIProvider):
    """Anthropic Claude AI provider."""
    
    BASE_URL = "https://api.anthropic.com/v1"
    API_VERSION = "2023-06-01"
    
    def __init__(self, config: ProviderConfig):
        self._provider_type = ProviderType.CLAUDE
        super().__init__(config)
    
    @property
    def provider_type(self) -> ProviderType:
        return self._provider_type
    
    def _initialize_client(self) -> None:
        """Initialize the HTTP client for Claude."""
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": self.API_VERSION,
        }
        if self.config.api_key:
            headers["x-api-key"] = self.config.api_key
        if self.config.extra.get("anthropic_beta"):
            headers["anthropic-beta"] = self.config.extra["anthropic_beta"]
        
        self._client = HTTPClient(
            base_url=self.config.base_url or self.BASE_URL,
            api_key=self.config.api_key,
            timeout=self.config.timeout,
            headers=headers,
            custom_headers=self.config.custom_headers,
        )
        self._client.provider_type = "claude"
    
    def get_available_models(self) -> List[ModelInfo]:
        """Return available Claude models."""
        return CLAUDE_MODELS
    
    def validate_config(self) -> bool:
        """Validate Claude configuration."""
        return self.config.api_key is not None
    
    async def health_check(self) -> bool:
        """Check if Claude API is accessible."""
        try:
            # Simple health check - just verify API key works
            await self._client.post(
                "/messages",
                json={
                    "model": "claude-3-haiku",
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "hi"}],
                }
            )
            self._health.status = ProviderStatus.AVAILABLE
            return True
        except Exception:
            self._health.status = ProviderStatus.UNAVAILABLE
            return False
    
    @log_provider_call("chat", "claude", "model")
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
        """Send a chat completion request to Claude."""
        model = model or self.config.model or "claude-3-sonnet"
        start_time = datetime.utcnow()
        
        # Build request payload
        system_message, chat_messages = self._split_system_message(messages)
        
        payload: Dict[str, Any] = {
            "model": model,
            "messages": [self._convert_message(m) for m in chat_messages],
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
        }
        
        if system_message:
            payload["system"] = system_message
        if stop:
            payload["stop_sequences"] = stop
        
        # Add tool use if supported
        if functions:
            payload["tools"] = [
                {
                    "name": f.name,
                    "description": f.description or "",
                    "input_schema": f.parameters or {"type": "object", "properties": {}},
                }
                for f in functions
            ]
        
        # Make request
        response = await self._client.post("/messages", json=payload)
        
        # Parse response
        content_blocks = response.get("content", [])
        content = ""
        function_call = None
        
        for block in content_blocks:
            if block.get("type") == "text":
                content += block.get("text", "")
            elif block.get("type") == "tool_use":
                function_call = FunctionCall(
                    name=block["name"],
                    arguments=json.dumps(block["input"]),
                    call_id=block["id"],
                )
                content = f"[Function call: {block['name']}]"
        
        finish_reason = response.get("stop_reason", "end_turn")
        
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
        """Send a streaming chat completion request to Claude."""
        model = model or self.config.model or "claude-3-sonnet"
        
        system_message, chat_messages = self._split_system_message(messages)
        
        payload: Dict[str, Any] = {
            "model": model,
            "messages": [self._convert_message(m) for m in chat_messages],
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
            "stream": True,
        }
        
        if system_message:
            payload["system"] = system_message
        if stop:
            payload["stop_sequences"] = stop
        
        full_content = ""
        finish_reason = None
        
        async for line in self._client.stream_post("/messages", json=payload):
            if line.startswith("data:"):
                data = json.loads(line[5:])
                
                if data.get("type") == "content_block_delta":
                    delta = data.get("delta", {})
                    if delta.get("type") == "text_delta":
                        token = delta.get("text", "")
                        full_content += token
                        yield StreamingChunk(
                            content=full_content,
                            delta=token,
                            is_final=False,
                        )
                
                elif data.get("type") == "message_delta":
                    finish_reason = data.get("delta", {}).get("stop_reason")
        
        yield StreamingChunk(
            content=full_content,
            delta="",
            is_final=True,
            finish_reason=finish_reason,
        )
    
    def _split_system_message(
        self,
        messages: List[Message]
    ) -> tuple[Optional[str], List[Message]]:
        """Split system message from other messages."""
        system = None
        chat_messages = []
        
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                if system is None:
                    system = ""
                system += msg.content if isinstance(msg.content, str) else ""
            else:
                chat_messages.append(msg)
        
        return system, chat_messages
    
    def _convert_message(self, message: Message) -> Dict[str, Any]:
        """Convert Message to Claude format."""
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
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": block.image_url,
                        }
                    })
            msg["content"] = content_parts
        
        return msg
    
    def _extract_usage(
        self,
        usage_data: Dict[str, Any],
        model: str
    ) -> TokenUsage:
        """Extract token usage from response."""
        prompt_tokens = usage_data.get("input_tokens", 0)
        completion_tokens = usage_data.get("output_tokens", 0)
        total_tokens = prompt_tokens + completion_tokens
        
        # Calculate cost
        model_info = next(
            (m for m in CLAUDE_MODELS if model in m.id),
            CLAUDE_MODELS[1]  # Default to Sonnet
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