"""Retry utilities with exponential backoff."""

import asyncio
import random
from dataclasses import dataclass, field
from typing import TypeVar, Callable, Awaitable, Optional, Type
from functools import wraps

from services.ai_provider.base import AIProviderError, RateLimitError, TimeoutError


T = TypeVar('T')


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple = (
        RateLimitError,
        TimeoutError,
        asyncio.TimeoutError,
        ConnectionError,
    )


@dataclass
class RetryState:
    """State tracking for retries."""
    attempt: int = 0
    last_delay: float = 0.0
    total_delay: float = 0.0
    errors: list = field(default_factory=list)


def calculate_delay(
    attempt: int,
    config: RetryConfig
) -> float:
    """Calculate delay for the given attempt number.
    
    Args:
        attempt: Current attempt number (0-indexed)
        config: Retry configuration
        
    Returns:
        Delay in seconds
    """
    delay = config.base_delay * (config.exponential_base ** attempt)
    delay = min(delay, config.max_delay)
    
    if config.jitter:
        delay = delay * (0.5 + random.random())
    
    return delay


async def retry_async(
    func: Callable[..., Awaitable[T]],
    *args,
    config: Optional[RetryConfig] = None,
    state: Optional[RetryState] = None,
    **kwargs
) -> T:
    """Retry an async function with exponential backoff.
    
    Args:
        func: Async function to retry
        *args: Positional arguments for the function
        config: Retry configuration
        state: Optional state tracker
        **kwargs: Keyword arguments for the function
        
    Returns:
        Result of the function
        
    Raises:
        Last exception if all retries exhausted
    """
    config = config or RetryConfig()
    state = state or RetryState()
    
    while state.attempt <= config.max_retries:
        try:
            return await func(*args, **kwargs)
        except config.retryable_exceptions as e:
            state.attempt += 1
            state.errors.append(e)
            
            if state.attempt > config.max_retries:
                raise
            
            delay = calculate_delay(state.attempt - 1, config)
            state.last_delay = delay
            state.total_delay += delay
            
            await asyncio.sleep(delay)
            
    raise state.errors[-1] if state.errors else Exception("Retry loop exited unexpectedly")


def retry_decorator(config: Optional[RetryConfig] = None):
    """Decorator to add retry behavior to async functions.
    
    Args:
        config: Retry configuration
        
    Returns:
        Decorated function
    """
    config = config or RetryConfig()
    
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await retry_async(func, *args, config=config, **kwargs)
        return wrapper
    return decorator


class CircuitBreaker:
    """Circuit breaker pattern for provider resilience."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._state = "closed"  # closed, open, half_open
        self._half_open_calls = 0
    
    @property
    def state(self) -> str:
        """Get current circuit breaker state."""
        if self._state == "open":
            if self._last_failure_time:
                import time
                if time.time() - self._last_failure_time >= self.recovery_timeout:
                    self._state = "half_open"
                    self._half_open_calls = 0
        return self._state
    
    def is_available(self) -> bool:
        """Check if calls are allowed."""
        return self.state != "open"
    
    def record_success(self) -> None:
        """Record a successful call."""
        self._failure_count = 0
        self._state = "closed"
    
    def record_failure(self) -> None:
        """Record a failed call."""
        import time
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        if self._failure_count >= self.failure_threshold:
            self._state = "open"
    
    def can_execute(self) -> bool:
        """Check if execution can proceed."""
        if self.state == "closed":
            return True
        if self.state == "half_open":
            return self._half_open_calls < self.half_open_max_calls
        return False
    
    def on_execute(self) -> None:
        """Called when execution starts."""
        if self.state == "half_open":
            self._half_open_calls += 1