"""Google Gemini provider implementation."""

import json
from typing import Optional, List, Dict, Any, AsyncIterator
from datetime import datetime

import httpx

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


GEMINI_MODELS = [
    ModelInfo(
        id="gemini-2.5-flash-preview-05-20",
        name="Gemini 2.5 Flash",
        provider=ProviderType.GEMINI,
        supports_function_calling=True,
        supports_vision=True,
        context_window=1048576,
    ),
    ModelInfo(
        id="gemini-1.5-pro",
        name="Gemini 1.5 Pro",
        provider=ProviderType.GEMINI,
        supports_function_calling=True,
        supports_vision=True,
        context_window=2097152,
        cost_per_input_token=0.00125,
        cost_per_output_token=0.005,
    ),
    ModelInfo(
        id="gemini-1.5-flash",
        name="Gemini 1.5 Flash",
        provider=ProviderType.GEMINI,
        supports_function_calling=True,
        supports_vision=True,
        context_window=1048576,
        cost_per_input_token=0.000075,
        cost_per_output_token=0.0003,
    ),
]


class GeminiProvider(BaseAIProvider):
    """Google Gemini AI provider."""
    
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
    
    def __init__(self, config: ProviderConfig):
        self._provider_type = ProviderType.GEMINI
        super().__init__(config)
    
    @property
    def provider_type(self) -> ProviderType:
        return self._provider_type
    
    def _initialize_client(self) -> None:
        """Initialize the HTTP client for Gemini."""
        headers = {
            "Content-Type": "application/json",
        }
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        
        base_url = self.config.base_url or self.BASE_URL
        
        self._client = HTTPClient(
            base_url=base_url,
            api_key=self.config.api_key,
            timeout=self.config.timeout,
            headers=headers,
            custom_headers=self.config.custom_headers,
        )
        self._client.provider_type = "gemini"
    
    def get_available_models(self) -> List[ModelInfo]:
        """Return available Gemini models."""
        return GEMINI_MODELS
    
    def validate_config(self) -> bool:
        """Validate Gemini configuration."""
        return self.config.api_key is not None or self.config.base_url is not None
    
    async def health_check(self) -> bool:
        """Check if Gemini API is accessible."""
        try:
            model = self.config.model or "gemini-1.5-flash"
            url = f"/models/{model}"
            await self._client.get(url)
            self._health.status = ProviderStatus.AVAILABLE
            return True
        except Exception:
            self._health.status = ProviderStatus.UNAVAILABLE
            return False
    
    @log_provider_call("chat", "gemini", "model")
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
        """Send a chat completion request to Gemini."""
        model = model or self.config.model or "gemini-1.5-flash"
        start_time = datetime.utcnow()
        
        # Build request payload
        contents = self._convert_messages_to_contents(messages)
        
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "topP": kwargs.get("top_p", 0.95),
                "topK": kwargs.get("top_k", 40),
                "maxOutputTokens": max_tokens or 2048,
            },
        }
        
        if stop:
            payload["generationConfig"]["stopSequences"] = stop
        
        # Add function calling if supported
        if functions:
            payload["tools"] = self._convert_functions_to_tools(functions)
        
        # Make request
        api_key = self.config.api_key or kwargs.get("api_key", "")
        url = f"/models/{model}:generateContent?key={api_key}"
        
        try:
            response = await self._client.post(url, json=payload)
            
            # Parse response
            content = self._parse_response(response)
            finish_reason = response.get("candidates", [{}])[0].get(
                "finishReason", "STOP"
            )
            
            # Extract usage
            usage = self._extract_usage(response, model)
            
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
            )
            
        except Exception as e:
            self.update_health(False, 0)
            raise
    
    async def stream(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> AsyncIterator[StreamingChunk]:
        """Send a streaming chat completion request to Gemini."""
        model = model or self.config.model or "gemini-1.5-flash"
        
        contents = self._convert_messages_to_contents(messages)
        
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "topP": kwargs.get("top_p", 0.95),
                "topK": kwargs.get("top_k", 40),
                "maxOutputTokens": max_tokens or 2048,
                "candidateCount": 1,
            },
        }
        
        if stop:
            payload["generationConfig"]["stopSequences"] = stop
        
        api_key = self.config.api_key or kwargs.get("api_key", "")
        url = f"/models/{model}:streamGenerateContent?key={api_key}&alt=sse"
        
        full_content = ""
        async for line in self._client.stream_post(url, json=payload):
            if line.startswith("data:"):
                data = json.loads(line[5:])
                if "candidates" in data:
                    content = data["candidates"][0]["content"]["parts"][0].get(
                        "text", ""
                    )
                    delta = content[len(full_content):]
                    full_content = content
                    
                    yield StreamingChunk(
                        content=full_content,
                        delta=delta,
                        is_final=False,
                    )
        
        yield StreamingChunk(
            content=full_content,
            delta="",
            is_final=True,
        )
    
    def _convert_messages_to_contents(
        self,
        messages: List[Message]
    ) -> List[Dict[str, Any]]:
        """Convert messages to Gemini format."""
        contents = []
        
        for msg in messages:
            role = "user" if msg.role.value == "user" else "model"
            
            if isinstance(msg.content, str):
                parts = [{"text": msg.content}]
            else:
                parts = []
                for block in msg.content:
                    if block.type.value == "text":
                        parts.append({"text": block.text})
                    elif block.type.value == "image":
                        parts.append({
                            "inlineData": {
                                "mimeType": "image/jpeg",
                                "data": block.image_url,
                            }
                        })
            
            contents.append({
                "role": role,
                "parts": parts,
            })
        
        return contents
    
    def _convert_functions_to_tools(
        self,
        functions: List[FunctionDefinition]
    ) -> List[Dict[str, Any]]:
        """Convert functions to Gemini tools format."""
        return [{
            "functionDeclarations": [
                {
                    "name": f.name,
                    "description": f.description or "",
                    "parameters": f.parameters or {"type": "object", "properties": {}},
                }
                for f in functions
            ]
        }]
    
    def _parse_response(self, response: Dict[str, Any]) -> str:
        """Parse Gemini response to extract content."""
        candidates = response.get("candidates", [])
        if not candidates:
            return ""
        
        parts = candidates[0].get("content", {}).get("parts", [])
        
        content_parts = []
        for part in parts:
            if "text" in part:
                content_parts.append(part["text"])
            elif "functionCall" in part:
                # Handle function calls
                fc = part["functionCall"]
                return f"[Function call: {fc['name']}]"
        
        return "\n".join(content_parts)
    
    def _extract_usage(
        self,
        response: Dict[str, Any],
        model: str
    ) -> TokenUsage:
        """Extract token usage from response."""
        usage = response.get("usageMetadata", {})
        
        prompt_tokens = usage.get("promptTokenCount", 0)
        completion_tokens = usage.get("candidatesTokenCount", 0)
        total_tokens = usage.get("totalTokenCount", 0)
        
        # Calculate cost (approximate)
        model_info = next(
            (m for m in GEMINI_MODELS if m.id == model),
            GEMINI_MODELS[-1]
        )
        cost = 0.0
        if model_info.cost_per_input_token:
            cost += prompt_tokens * model_info.cost_per_input_token
        if model_info.cost_per_output_token:
            cost += completion_tokens * model_info.cost_per_output_token
        
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