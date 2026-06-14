"""HTTP client utilities for AI providers."""

import asyncio
import httpx
from typing import Optional, Dict, Any, AsyncIterator
import time

from services.ai_provider.base import (
    ProviderConfig,
    AIProviderError,
    AuthenticationError,
    RateLimitError,
    TimeoutError,
    InvalidRequestError,
)


class HTTPClient:
    """Async HTTP client with retry and timeout support."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 60.0,
        headers: Optional[Dict[str, str]] = None,
        custom_headers: Optional[Dict[str, str]] = None,
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout
        self.default_headers = headers or {}
        self.custom_headers = custom_headers or {}
        
        self._client: Optional[httpx.AsyncClient] = None
    
    def _build_headers(self, additional: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Build request headers."""
        headers = {
            **self.default_headers,
            **self.custom_headers,
            **(additional or {}),
        }
        return headers
    
    async def __aenter__(self):
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def acquire(self) -> None:
        """Acquire the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
                headers=self._build_headers(),
            )
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make a GET request."""
        await self.acquire()
        try:
            response = await self._client.get(
                url,
                headers=self._build_headers(headers),
                params=params,
            )
            return self._handle_response(response)
        except httpx.TimeoutException as e:
            raise TimeoutError(f"Request timed out: {e}", provider=getattr(self, 'provider_type', None))
    
    async def post(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make a POST request."""
        await self.acquire()
        try:
            response = await self._client.post(
                url,
                data=data,
                json=json,
                headers=self._build_headers(headers),
            )
            return self._handle_response(response)
        except httpx.TimeoutException as e:
            raise TimeoutError(f"Request timed out: {e}", provider=getattr(self, 'provider_type', None))
    
    async def stream_post(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> AsyncIterator[str]:
        """Make a streaming POST request."""
        await self.acquire()
        
        request = self._client.build_request(
            "POST",
            url,
            json=json,
            headers=self._build_headers(headers),
        )
        
        try:
            async with self._client.stream(request) as response:
                self._handle_status_code(response.status_code, response.text)
                async for line in response.aiter_lines():
                    if line.strip():
                        yield line
        except httpx.TimeoutException as e:
            raise TimeoutError(f"Request timed out: {e}", provider=getattr(self, 'provider_type', None))
    
    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Handle HTTP response."""
        status_code = response.status_code
        
        if status_code == 200:
            return response.json()
        
        self._handle_status_code(status_code, response.text)
        return response.json()
    
    def _handle_status_code(
        self,
        status_code: int,
        response_text: str,
        provider: Optional[str] = None
    ) -> None:
        """Handle HTTP status codes and raise appropriate errors."""
        if status_code == 200:
            return
        
        error_message = response_text
        try:
            error_data = response.json()
            error_message = error_data.get('error', {}).get('message', response_text)
        except:
            pass
        
        if status_code == 401:
            raise AuthenticationError(
                f"Authentication failed: {error_message}",
                provider=provider
            )
        elif status_code == 403:
            raise AuthenticationError(
                f"Access forbidden: {error_message}",
                provider=provider
            )
        elif status_code == 429:
            retry_after = None
            if 'retry-after' in response_text.lower():
                import re
                match = re.search(r'retry-after:\s*(\d+)', response_text, re.IGNORECASE)
                if match:
                    retry_after = float(match.group(1))
            raise RateLimitError(
                f"Rate limit exceeded: {error_message}",
                provider=provider,
                retry_after=retry_after
            )
        elif status_code == 400:
            raise InvalidRequestError(
                f"Invalid request: {error_message}",
                provider=provider
            )
        else:
            raise AIProviderError(
                f"HTTP {status_code}: {error_message}",
                provider=provider
            )


class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self, requests_per_minute: int):
        self.requests_per_minute = requests_per_minute
        self.interval = 60.0 / requests_per_minute
        self._last_request_time = 0.0
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        """Acquire permission to make a request."""
        async with self._lock:
            now = time.time()
            time_since_last = now - self._last_request_time
            
            if time_since_last < self.interval:
                wait_time = self.interval - time_since_last
                await asyncio.sleep(wait_time)
            
            self._last_request_time = time.time()


def estimate_token_count(text: str, model: Optional[str] = None) -> int:
    """Estimate token count for text.
    
    This is a rough approximation. For accurate counts,
    use the tokenizer specific to each provider.
    
    Args:
        text: Input text
        model: Optional model identifier
        
    Returns:
        Estimated token count
    """
    # Rough estimation: ~4 characters per token for English
    # This varies significantly by language and content type
    return len(text) // 4 + 1