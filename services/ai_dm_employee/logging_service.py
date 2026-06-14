"""AI DM Logging Service - Comprehensive logging for debugging and compliance."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Optional
from enum import Enum
import json
import threading
from collections import deque
import os


class LogLevel(Enum):
    """Log levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogCategory(Enum):
    """Categories of log entries."""
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_PROCESSING = "message_processing"
    CONTEXT_LOADED = "context_loaded"
    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"
    AI_REQUEST = "ai_request"
    AI_RESPONSE = "ai_response"
    SAFETY_CHECK = "safety_check"
    MODERATION_CHECK = "moderation_check"
    HALLUCINATION_CHECK = "hallucination_check"
    RESPONSE_SENT = "response_sent"
    HUMAN_TAKEOVER = "human_takeover"
    ERROR = "error"
    METRICS = "metrics"


@dataclass
class LogEntry:
    """A single log entry."""
    id: str
    timestamp: datetime
    level: LogLevel
    category: LogCategory
    message: str
    conversation_id: str
    business_id: str
    
    # Data
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Performance
    duration_ms: Optional[float] = None
    
    # Error info
    error: Optional[str] = None
    stack_trace: Optional[str] = None
    
    # User/AI identifiers
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "category": self.category.value,
            "message": self.message,
            "conversation_id": self.conversation_id,
            "business_id": self.business_id,
            "data": self.data,
            "metadata": self.metadata,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "stack_trace": self.stack_trace,
            "user_id": self.user_id,
            "request_id": self.request_id,
        }


@dataclass
class AIDMLogSession:
    """A complete AI DM session for a conversation."""
    session_id: str
    conversation_id: str
    business_id: str
    user_id: Optional[str] = None
    
    # Timeline
    started_at: datetime = field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    
    # Messages
    user_messages: List[Dict[str, Any]] = field(default_factory=list)
    ai_responses: List[Dict[str, Any]] = field(default_factory=list)
    
    # Performance
    total_interactions: int = 0
    total_processing_time_ms: float = 0.0
    avg_response_time_ms: float = 0.0
    
    # Outcomes
    human_takeovers: int = 0
    errors: int = 0
    safety_flags: int = 0
    hallucination_flags: int = 0
    
    # Final status
    status: str = "active"  # active, completed, error, escalated
    
    # Log entries
    log_entries: List[str] = field(default_factory=list)  # Log entry IDs
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "business_id": self.business_id,
            "user_id": self.user_id,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "user_messages": self.user_messages,
            "ai_responses": self.ai_responses,
            "total_interactions": self.total_interactions,
            "total_processing_time_ms": self.total_processing_time_ms,
            "avg_response_time_ms": self.avg_response_time_ms,
            "human_takeovers": self.human_takeovers,
            "errors": self.errors,
            "safety_flags": self.safety_flags,
            "hallucination_flags": self.hallucination_flags,
            "status": self.status,
            "log_entries_count": len(self.log_entries),
        }


class AIDMLoggingService:
    """Comprehensive logging service for AI DM operations.
    
    Responsibilities:
    - Log all AI DM operations
    - Track conversation sessions
    - Record performance metrics
    - Support debugging and compliance
    - Provide analytics data
    """
    
    def __init__(
        self,
        max_entries: int = 10000,
        log_dir: Optional[str] = None,
        session_timeout_minutes: int = 60,
    ):
        """Initialize the logging service.
        
        Args:
            max_entries: Maximum log entries to keep in memory
            log_dir: Directory for persistent log files
            session_timeout_minutes: Minutes before a session is considered inactive
        """
        self._entries: deque = deque(maxlen=max_entries)
        self._sessions: Dict[str, AIDMLogSession] = {}
        self._current_session: Optional[str] = None
        
        self._log_dir = log_dir
        self._session_timeout = timedelta(minutes=session_timeout_minutes)
        
        # Lock for thread safety
        self._lock = threading.Lock()
        
        # Statistics
        self._stats = {
            "total_entries": 0,
            "total_sessions": 0,
            "entries_by_level": {},
            "entries_by_category": {},
            "errors_logged": 0,
        }
        
        # ID counters
        self._entry_counter = 0
        self._session_counter = 0
        
        # Create log directory if specified
        if self._log_dir and not os.path.exists(self._log_dir):
            os.makedirs(self._log_dir, exist_ok=True)
    
    def _generate_id(self, prefix: str) -> str:
        """Generate a unique ID."""
        with self._lock:
            if prefix == "log":
                self._entry_counter += 1
                return f"log_{self._entry_counter:08d}"
            elif prefix == "session":
                self._session_counter += 1
                return f"session_{self._session_counter:08d}"
            else:
                import uuid
                return f"{prefix}_{uuid.uuid4().hex[:8]}"
    
    def start_session(
        self,
        conversation_id: str,
        business_id: str,
        user_id: Optional[str] = None,
    ) -> str:
        """Start a new logging session.
        
        Args:
            conversation_id: Conversation identifier
            business_id: Business identifier
            user_id: Optional user identifier
            
        Returns:
            Session ID
        """
        session_id = self._generate_id("session")
        
        session = AIDMLogSession(
            session_id=session_id,
            conversation_id=conversation_id,
            business_id=business_id,
            user_id=user_id,
        )
        
        with self._lock:
            self._sessions[session_id] = session
            self._current_session = session_id
            self._stats["total_sessions"] += 1
        
        self.log(
            level=LogLevel.INFO,
            category=LogCategory.MESSAGE_RECEIVED,
            message="Session started",
            conversation_id=conversation_id,
            business_id=business_id,
            user_id=user_id,
            data={"session_id": session_id},
        )
        
        return session_id
    
    def end_session(self, session_id: Optional[str] = None, status: str = "completed") -> bool:
        """End a logging session.
        
        Args:
            session_id: Session to end (uses current if not specified)
            status: Final session status
            
        Returns:
            True if session was ended
        """
        if session_id is None:
            session_id = self._current_session
        
        if not session_id or session_id not in self._sessions:
            return False
        
        session = self._sessions[session_id]
        session.ended_at = datetime.utcnow()
        session.status = status
        
        # Calculate final statistics
        if session.total_interactions > 0:
            session.avg_response_time_ms = (
                session.total_processing_time_ms / session.total_interactions
            )
        
        self.log(
            level=LogLevel.INFO,
            category=LogCategory.MESSAGE_PROCESSING,
            message="Session ended",
            conversation_id=session.conversation_id,
            business_id=session.business_id,
            data={
                "session_id": session_id,
                "status": status,
                "total_interactions": session.total_interactions,
                "total_time_ms": session.total_processing_time_ms,
            },
        )
        
        self._current_session = None
        return True
    
    def log(
        self,
        level: LogLevel,
        category: LogCategory,
        message: str,
        conversation_id: str,
        business_id: str,
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
        error: Optional[str] = None,
        stack_trace: Optional[str] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> str:
        """Log an entry.
        
        Args:
            level: Log level
            category: Log category
            message: Log message
            conversation_id: Conversation identifier
            business_id: Business identifier
            data: Optional data dictionary
            metadata: Optional metadata
            duration_ms: Optional duration in milliseconds
            error: Optional error message
            stack_trace: Optional stack trace
            user_id: Optional user identifier
            request_id: Optional request identifier
            
        Returns:
            Log entry ID
        """
        entry_id = self._generate_id("log")
        
        entry = LogEntry(
            id=entry_id,
            timestamp=datetime.utcnow(),
            level=level,
            category=category,
            message=message,
            conversation_id=conversation_id,
            business_id=business_id,
            data=data or {},
            metadata=metadata or {},
            duration_ms=duration_ms,
            error=error,
            stack_trace=stack_trace,
            user_id=user_id,
            request_id=request_id,
        )
        
        with self._lock:
            self._entries.append(entry)
            self._stats["total_entries"] += 1
            
            # Update stats
            level_key = level.value
            self._stats["entries_by_level"][level_key] = (
                self._stats["entries_by_level"].get(level_key, 0) + 1
            )
            
            category_key = category.value
            self._stats["entries_by_category"][category_key] = (
                self._stats["entries_by_category"].get(category_key, 0) + 1
            )
            
            if level in (LogLevel.ERROR, LogLevel.CRITICAL):
                self._stats["errors_logged"] += 1
            
            # Link to current session
            if self._current_session:
                session = self._sessions.get(self._current_session)
                if session:
                    session.log_entries.append(entry_id)
        
        # Persist to file if directory is configured
        if self._log_dir:
            self._persist_entry(entry)
        
        return entry_id
    
    def log_message_received(
        self,
        conversation_id: str,
        business_id: str,
        message: str,
        user_id: Optional[str] = None,
    ) -> str:
        """Log a received message."""
        return self.log(
            level=LogLevel.INFO,
            category=LogCategory.MESSAGE_RECEIVED,
            message=f"Received message: {message[:100]}...",
            conversation_id=conversation_id,
            business_id=business_id,
            user_id=user_id,
            data={"message_length": len(message)},
        )
    
    def log_ai_request(
        self,
        conversation_id: str,
        business_id: str,
        prompt: str,
        model: str,
        provider: str,
    ) -> str:
        """Log an AI API request."""
        return self.log(
            level=LogLevel.DEBUG,
            category=LogCategory.AI_REQUEST,
            message=f"AI request to {provider}/{model}",
            conversation_id=conversation_id,
            business_id=business_id,
            data={
                "model": model,
                "provider": provider,
                "prompt_length": len(prompt),
            },
        )
    
    def log_ai_response(
        self,
        conversation_id: str,
        business_id: str,
        response: str,
        provider: str,
        duration_ms: float,
        tokens_used: Optional[int] = None,
    ) -> str:
        """Log an AI API response."""
        return self.log(
            level=LogLevel.DEBUG,
            category=LogCategory.AI_RESPONSE,
            message=f"AI response from {provider}",
            conversation_id=conversation_id,
            business_id=business_id,
            duration_ms=duration_ms,
            data={
                "response_length": len(response),
                "tokens_used": tokens_used,
                "provider": provider,
            },
        )
    
    def log_safety_check(
        self,
        conversation_id: str,
        business_id: str,
        passed: bool,
        concerns: List[str],
    ) -> str:
        """Log a safety check."""
        return self.log(
            level=LogLevel.WARNING if not passed else LogLevel.INFO,
            category=LogCategory.SAFETY_CHECK,
            message="Safety check " + ("passed" if passed else "failed"),
            conversation_id=conversation_id,
            business_id=business_id,
            data={
                "passed": passed,
                "concerns": concerns,
            },
        )
    
    def log_human_takeover(
        self,
        conversation_id: str,
        business_id: str,
        reason: str,
    ) -> str:
        """Log a human takeover request."""
        return self.log(
            level=LogLevel.INFO,
            category=LogCategory.HUMAN_TAKEOVER,
            message=f"Human takeover requested: {reason}",
            conversation_id=conversation_id,
            business_id=business_id,
            data={"reason": reason},
        )
    
    def log_error(
        self,
        conversation_id: str,
        business_id: str,
        error: str,
        stack_trace: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Log an error."""
        return self.log(
            level=LogLevel.ERROR,
            category=LogCategory.ERROR,
            message=f"Error: {error}",
            conversation_id=conversation_id,
            business_id=business_id,
            error=error,
            stack_trace=stack_trace,
            data=context or {},
        )
    
    def _persist_entry(self, entry: LogEntry) -> None:
        """Persist a log entry to file."""
        if not self._log_dir:
            return
        
        try:
            filename = f"{entry.timestamp.strftime('%Y%m%d')}.jsonl"
            filepath = os.path.join(self._log_dir, filename)
            
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + '\n')
        except Exception:
            pass  # Fail silently for persistence
    
    def get_entries(
        self,
        conversation_id: Optional[str] = None,
        business_id: Optional[str] = None,
        level: Optional[LogLevel] = None,
        category: Optional[LogCategory] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[LogEntry]:
        """Get log entries with filters.
        
        Args:
            conversation_id: Filter by conversation
            business_id: Filter by business
            level: Filter by log level
            category: Filter by category
            limit: Maximum entries to return
            offset: Offset for pagination
            
        Returns:
            List of log entries
        """
        results = []
        
        with self._lock:
            entries_list = list(self._entries)
        
        for entry in entries_list:
            # Apply filters
            if conversation_id and entry.conversation_id != conversation_id:
                continue
            if business_id and entry.business_id != business_id:
                continue
            if level and entry.level != level:
                continue
            if category and entry.category != category:
                continue
            
            results.append(entry)
        
        # Apply pagination
        return results[offset:offset+limit]
    
    def get_session(self, session_id: str) -> Optional[AIDMLogSession]:
        """Get a session by ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            AIDMLogSession or None
        """
        return self._sessions.get(session_id)
    
    def get_session_logs(
        self,
        session_id: str,
        limit: int = 100,
    ) -> List[LogEntry]:
        """Get all logs for a session.
        
        Args:
            session_id: Session identifier
            limit: Maximum entries
            
        Returns:
            List of log entries
        """
        session = self._sessions.get(session_id)
        if not session:
            return []
        
        return self.get_entries(
            conversation_id=session.conversation_id,
            limit=limit,
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get logging statistics.
        
        Returns:
            Statistics dictionary
        """
        with self._lock:
            active_sessions = sum(
                1 for s in self._sessions.values()
                if s.status == "active"
            )
        
        return {
            **self._stats,
            "active_sessions": active_sessions,
            "total_sessions": len(self._sessions),
            "memory_entries": len(self._entries),
        }
    
    def clear_old_entries(self, hours: int = 24) -> int:
        """Clear log entries older than specified hours.
        
        Args:
            hours: Hours to keep
            
        Returns:
            Number of entries cleared
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        cleared = 0
        
        with self._lock:
            while self._entries and self._entries[0].timestamp < cutoff:
                self._entries.popleft()
                cleared += 1
        
        return cleared
    
    def export_logs(
        self,
        conversation_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        format: str = "json",
    ) -> str:
        """Export logs to string.
        
        Args:
            conversation_id: Filter by conversation
            start_time: Start time filter
            end_time: End time filter
            format: Output format (json, csv)
            
        Returns:
            Export string
        """
        entries = self.get_entries(
            conversation_id=conversation_id,
            limit=10000,
        )
        
        # Apply time filters
        if start_time:
            entries = [e for e in entries if e.timestamp >= start_time]
        if end_time:
            entries = [e for e in entries if e.timestamp <= end_time]
        
        if format == "json":
            return json.dumps(
                [e.to_dict() for e in entries],
                indent=2,
                ensure_ascii=False,
            )
        elif format == "csv":
            lines = ["timestamp,level,category,message,conversation_id"]
            for e in entries:
                lines.append(
                    f"{e.timestamp.isoformat()},{e.level.value},"
                    f"{e.category.value},\"{e.message}\",{e.conversation_id}"
                )
            return '\n'.join(lines)
        
        return ""
