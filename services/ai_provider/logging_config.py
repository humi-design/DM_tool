"""Comprehensive logging for AI providers."""

import logging
import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from contextvars import ContextVar
from functools import wraps
import asyncio

if TYPE_CHECKING:
    from services.ai_provider.base import (
        ProviderType, 
        ChatCompletionResponse, 
        Message,
        TokenUsage,
    )


class LogLevel(Enum):
    """Log levels for AI operations."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ProviderCallLog:
    """Structured log entry for a provider call."""
    timestamp: str
    request_id: str
    provider: str
    model: str
    operation: str
    duration_ms: float
    status: str
    error: Optional[str] = None
    token_usage: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class TokenUsageLog:
    """Token usage logging data."""
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float
    timestamp: str


# Context variables for request tracking
_current_request_id: ContextVar[Optional[str]] = ContextVar('current_request_id', default=None)
_current_provider: ContextVar[Optional[str]] = ContextVar('current_provider', default=None)


class AIProviderLogger:
    """Centralized logging for AI provider operations."""
    
    def __init__(
        self,
        name: str = "ai_providers",
        level: str = "INFO",
        format_json: bool = False,
        log_to_file: bool = False,
        log_file_path: Optional[str] = None,
    ):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        self.format_json = format_json
        
        # Console handler
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            )
            self.logger.addHandler(handler)
        
        # File handler if requested
        if log_to_file and log_file_path:
            file_handler = logging.FileHandler(log_file_path)
            file_handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            )
            self.logger.addHandler(file_handler)
        
        # Metrics tracking
        self._metrics: Dict[str, List[float]] = {}
        self._error_counts: Dict[str, int] = {}
        self._usage_totals: Dict[str, Dict[str, float]] = {}
    
    def set_request_context(self, request_id: str, provider: Optional[str] = None) -> None:
        """Set context for the current request."""
        _current_request_id.set(request_id)
        if provider:
            _current_provider.set(provider)
    
    def clear_request_context(self) -> None:
        """Clear the current request context."""
        _current_request_id.set(None)
        _current_provider.set(None)
    
    def _format_message(self, level: str, message: str, **kwargs) -> str:
        """Format log message."""
        context = {
            "request_id": _current_request_id.get(),
            "provider": _current_provider.get(),
        }
        context.update(kwargs)
        
        if self.format_json:
            return json.dumps({
                "level": level,
                "message": message,
                "timestamp": datetime.utcnow().isoformat(),
                **context
            })
        return f"{message} | {json.dumps(context)}"
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self.logger.debug(self._format_message("DEBUG", message, **kwargs))
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self.logger.info(self._format_message("INFO", message, **kwargs))
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self.logger.warning(self._format_message("WARNING", message, **kwargs))
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self.logger.error(self._format_message("ERROR", message, **kwargs))
    
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        self.logger.critical(self._format_message("CRITICAL", message, **kwargs))
    
    def log_provider_call(
        self,
        provider: str,
        model: str,
        operation: str,
        duration_ms: float,
        status: str,
        request_id: Optional[str] = None,
        error: Optional[str] = None,
        token_usage: Optional[Dict[str, Any]] = None,
        retry_count: int = 0,
        **metadata
    ) -> None:
        """Log a provider call with structured data."""
        log_entry = ProviderCallLog(
            timestamp=datetime.utcnow().isoformat(),
            request_id=request_id or _current_request_id.get() or "unknown",
            provider=provider,
            model=model,
            operation=operation,
            duration_ms=duration_ms,
            status=status,
            error=error,
            token_usage=token_usage,
            retry_count=retry_count,
            metadata=metadata,
        )
        
        if status == "success":
            self.info(
                f"Provider call completed",
                **asdict(log_entry)
            )
        else:
            self.error(
                f"Provider call failed: {error}",
                **asdict(log_entry)
            )
        
        # Update metrics
        self._update_metrics(provider, duration_ms, status, token_usage)
    
    def _update_metrics(
        self,
        provider: str,
        duration_ms: float,
        status: str,
        token_usage: Optional[Dict[str, Any]]
    ) -> None:
        """Update internal metrics."""
        if provider not in self._metrics:
            self._metrics[provider] = []
            self._error_counts[provider] = 0
        
        self._metrics[provider].append(duration_ms)
        
        if status != "success":
            self._error_counts[provider] += 1
        
        if token_usage:
            if provider not in self._usage_totals:
                self._usage_totals[provider] = {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "cost": 0.0
                }
            for key in self._usage_totals[provider]:
                if key in token_usage:
                    self._usage_totals[provider][key] += token_usage[key]
    
    def log_token_usage(self, usage: 'TokenUsageLog') -> None:
        """Log token usage."""
        self.info(
            f"Token usage: {usage.total_tokens} tokens, ${usage.cost:.4f}",
            provider=usage.provider,
            model=usage.model,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            cost=usage.cost,
        )
    
    def get_metrics(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """Get metrics for a provider or all providers."""
        if provider:
            return self._get_provider_metrics(provider)
        
        return {
            p: self._get_provider_metrics(p) 
            for p in self._metrics.keys()
        }
    
    def _get_provider_metrics(self, provider: str) -> Dict[str, Any]:
        """Get metrics for a specific provider."""
        if provider not in self._metrics:
            return {}
        
        durations = self._metrics[provider]
        sorted_durations = sorted(durations)
        n = len(sorted_durations)
        
        return {
            "call_count": len(durations),
            "error_count": self._error_counts.get(provider, 0),
            "error_rate": self._error_counts.get(provider, 0) / max(len(durations), 1),
            "latency_ms": {
                "min": min(durations),
                "max": max(durations),
                "avg": sum(durations) / len(durations),
                "p50": sorted_durations[int(n * 0.5)],
                "p95": sorted_durations[int(n * 0.95)],
                "p99": sorted_durations[int(n * 0.99)],
            },
            "usage": self._usage_totals.get(provider, {}),
        }
    
    def reset_metrics(self, provider: Optional[str] = None) -> None:
        """Reset metrics."""
        if provider:
            self._metrics.pop(provider, None)
            self._error_counts.pop(provider, None)
            self._usage_totals.pop(provider, None)
        else:
            self._metrics.clear()
            self._error_counts.clear()
            self._usage_totals.clear()


def log_provider_call(
    operation: str,
    provider: str,
    model: str,
    include_messages: bool = False,
    include_response: bool = False,
):
    """Decorator to automatically log provider calls.
    
    Args:
        operation: Operation name (e.g., 'chat', 'stream')
        provider: Provider name
        model: Model name
        include_messages: Whether to log message content
        include_response: Whether to log response content
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            from services.ai_provider.base import Message
            
            logger = getattr(self, '_logger', None) or _default_logger
            
            # Extract parameters for logging
            messages = kwargs.get('messages', [])
            if include_messages and messages:
                msg_summary = [
                    f"[{m.role.value}]: {m.content[:100]}..." if isinstance(m.content, str) and len(m.content) > 100 else f"[{m.role.value}]: {m.content}"
                    for m in messages[:3]
                ]
                kwargs['messages'] = messages
            
            start_time = time.time()
            status = "success"
            error = None
            retry_count = kwargs.get('retry_count', 0)
            
            try:
                result = await func(self, *args, **kwargs)
                
                # Log token usage if available
                if hasattr(result, 'usage') and result.usage:
                    logger.log_token_usage(TokenUsageLog(
                        provider=provider,
                        model=model,
                        prompt_tokens=result.usage.prompt_tokens,
                        completion_tokens=result.usage.completion_tokens,
                        total_tokens=result.usage.total_tokens,
                        cost=result.usage.cost,
                        timestamp=datetime.utcnow().isoformat(),
                    ))
                
                return result
                
            except Exception as e:
                status = "error"
                error = str(e)
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                
                logger.log_provider_call(
                    provider=provider,
                    model=model,
                    operation=operation,
                    duration_ms=duration_ms,
                    status=status,
                    error=error,
                    retry_count=retry_count,
                )
        
        return wrapper
    return decorator


# Default logger instance
_default_logger = AIProviderLogger()


def get_logger() -> AIProviderLogger:
    """Get the default logger instance."""
    return _default_logger


def set_logger(logger: AIProviderLogger) -> None:
    """Set the default logger instance."""
    global _default_logger
    _default_logger = logger