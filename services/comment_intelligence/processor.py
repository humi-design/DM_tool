"""Comment Processor - High-level processor for Instagram comments.

This module provides a simplified interface for processing Instagram
comments through the Comment Intelligence Engine.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

from services.comment_intelligence.engine import (
    CommentIntelligenceEngine,
    EngineConfig,
    ProcessingResult,
)
from services.comment_intelligence.intent import IntentType
from services.comment_intelligence.decision import ActionType


@dataclass
class ProcessedComment:
    """Processed comment with all relevant information."""
    # Original data
    comment_id: Optional[str]
    comment_text: str
    author_username: Optional[str]
    
    # Intent analysis
    intent: str
    intent_confidence: float
    intent_reasoning: str
    
    # Response
    response: Optional[str]
    should_reply: bool
    
    # Actions
    actions: List[str]
    primary_action: str
    
    # Emoji reactions
    has_emoji: bool
    emoji_responses: List[str]
    
    # Metadata
    processing_time_ms: float
    timestamp: datetime
    
    @classmethod
    def from_result(cls, result: ProcessingResult) -> "ProcessedComment":
        """Create from ProcessingResult."""
        emoji_responses = [r["response"] for r in result.emoji_reactions if r.get("response")]
        
        return cls(
            comment_id=result.request_id,
            comment_text=result.comment_text,
            author_username=result.author_username,
            intent=result.intent.value if result.intent else "other",
            intent_confidence=result.intent_confidence,
            intent_reasoning=result.intent_reasoning,
            response=result.response_content,
            should_reply=result.should_auto_reply,
            actions=[
                a.get("action_type", "unknown") 
                for a in (result.decision.get("actions", []) if result.decision else [])
            ],
            primary_action=(
                result.decision.get("primary_action", "log_only") 
                if result.decision else "log_only"
            ),
            has_emoji=len(result.emoji_reactions) > 0,
            emoji_responses=emoji_responses,
            processing_time_ms=result.processing_time_ms,
            timestamp=result.timestamp,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "comment_id": self.comment_id,
            "comment_text": self.comment_text,
            "author_username": self.author_username,
            "intent": self.intent,
            "intent_confidence": self.intent_confidence,
            "intent_reasoning": self.intent_reasoning,
            "response": self.response,
            "should_reply": self.should_reply,
            "actions": self.actions,
            "primary_action": self.primary_action,
            "has_emoji": self.has_emoji,
            "emoji_responses": self.emoji_responses,
            "processing_time_ms": self.processing_time_ms,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ProcessingStats:
    """Statistics for comment processing."""
    total_processed: int = 0
    by_intent: Dict[str, int] = field(default_factory=dict)
    average_confidence: float = 0.0
    average_processing_time_ms: float = 0.0
    auto_replies_sent: int = 0
    escalated_to_human: int = 0
    errors: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_processed": self.total_processed,
            "by_intent": self.by_intent,
            "average_confidence": self.average_confidence,
            "average_processing_time_ms": self.average_processing_time_ms,
            "auto_replies_sent": self.auto_replies_sent,
            "escalated_to_human": self.escalated_to_human,
            "errors": self.errors,
        }


class CommentProcessor:
    """High-level processor for Instagram comments.
    
    This class provides a simplified interface for processing comments
    through the Comment Intelligence pipeline, with built-in support for
    Instagram-specific features.
    """
    
    def __init__(
        self,
        engine: Optional[CommentIntelligenceEngine] = None,
        config: Optional[EngineConfig] = None
    ):
        """Initialize the comment processor.
        
        Args:
            engine: Optional pre-configured engine
            config: Optional engine configuration
        """
        self._engine = engine or CommentIntelligenceEngine(config)
        self._stats = ProcessingStats()
        self._logger = logging.getLogger("comment_processor")
    
    @property
    def engine(self) -> CommentIntelligenceEngine:
        """Get the underlying engine."""
        return self._engine
    
    @property
    def stats(self) -> ProcessingStats:
        """Get processing statistics."""
        return self._stats
    
    async def process_comment(
        self,
        text: str,
        author_username: Optional[str] = None,
        comment_id: Optional[str] = None,
        is_reply: bool = False,
        parent_comment: Optional[str] = None,
        **kwargs
    ) -> ProcessedComment:
        """Process a single Instagram comment.
        
        Args:
            text: Comment text
            author_username: Author's username
            comment_id: Instagram comment ID
            is_reply: Whether this is a reply to another comment
            parent_comment: Text of the parent comment if reply
            **kwargs: Additional context
            
        Returns:
            ProcessedComment with all analysis and response
        """
        context = {
            "is_reply": is_reply,
            "parent_comment": parent_comment,
            "comment_id": comment_id,
            **kwargs
        }
        
        result = await self._engine.process(
            comment_text=text,
            author_username=author_username,
            context=context,
        )
        
        # Update statistics
        self._update_stats(result)
        
        return ProcessedComment.from_result(result)
    
    async def process_webhook_payload(
        self,
        payload: Dict[str, Any]
    ) -> ProcessedComment:
        """Process a webhook payload from Instagram.
        
        Args:
            payload: Webhook payload from Instagram
            
        Returns:
            ProcessedComment with analysis
        """
        # Extract data from Instagram webhook format
        entry = payload.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        
        value = changes.get("value", {})
        
        comment_text = value.get("text", "")
        author_username = value.get("from", {}).get("username")
        comment_id = value.get("id")
        is_reply = bool(value.get("parent_id"))
        parent_id = value.get("parent_id")
        
        # Get parent comment if reply
        parent_comment = None
        if is_reply and parent_id:
            # In a real implementation, fetch the parent comment
            parent_comment = None
        
        return await self.process_comment(
            text=comment_text,
            author_username=author_username,
            comment_id=comment_id,
            is_reply=is_reply,
            parent_comment=parent_comment,
            source="instagram_webhook",
            instagram_comment_id=comment_id,
        )
    
    async def process_batch(
        self,
        comments: List[Dict[str, Any]]
    ) -> List[ProcessedComment]:
        """Process multiple comments.
        
        Args:
            comments: List of comment dicts with 'text' and optional 'author'
            
        Returns:
            List of ProcessedComment
        """
        results = await self._engine.process_batch([
            {
                "text": c.get("text", c.get("comment_text", "")),
                "author": c.get("author", c.get("author_username")),
                "context": c.get("context"),
            }
            for c in comments
        ])
        
        processed = [ProcessedComment.from_result(r) for r in results]
        
        # Update stats
        for result in results:
            self._update_stats(result)
        
        return processed
    
    def get_comments_for_auto_reply(
        self,
        processed_comments: List[ProcessedComment]
    ) -> List[ProcessedComment]:
        """Get comments that should receive auto-replies.
        
        Args:
            processed_comments: List of processed comments
            
        Returns:
            Filtered list of comments that need auto-reply
        """
        return [
            c for c in processed_comments
            if c.should_reply and c.response
        ]
    
    def get_comments_for_review(
        self,
        processed_comments: List[ProcessedComment]
    ) -> List[ProcessedComment]:
        """Get comments that need human review.
        
        Args:
            processed_comments: List of processed comments
            
        Returns:
            Filtered list of comments needing review
        """
        review_actions = {"flag_for_review", "escalate_to_human"}
        return [
            c for c in processed_comments
            if c.primary_action in review_actions
        ]
    
    def get_leads(
        self,
        processed_comments: List[ProcessedComment]
    ) -> List[Dict[str, Any]]:
        """Extract lead information from processed comments.
        
        Args:
            processed_comments: List of processed comments
            
        Returns:
            List of lead data dictionaries
        """
        lead_intents = {"interest", "price", "booking", "order"}
        leads = []
        
        for comment in processed_comments:
            if comment.intent in lead_intents and comment.author_username:
                leads.append({
                    "username": comment.author_username,
                    "intent": comment.intent,
                    "comment_text": comment.comment_text,
                    "confidence": comment.intent_confidence,
                    "timestamp": comment.timestamp.isoformat(),
                })
        
        return leads
    
    def _update_stats(self, result: ProcessingResult) -> None:
        """Update processing statistics."""
        self._stats.total_processed += 1
        
        if result.intent:
            intent_key = result.intent.value
            self._stats.by_intent[intent_key] = self._stats.by_intent.get(intent_key, 0) + 1
        
        # Calculate running average
        n = self._stats.total_processed
        self._stats.average_confidence = (
            (self._stats.average_confidence * (n - 1) + result.intent_confidence) / n
        )
        self._stats.average_processing_time_ms = (
            (self._stats.average_processing_time_ms * (n - 1) + result.processing_time_ms) / n
        )
        
        if result.should_auto_reply:
            self._stats.auto_replies_sent += 1
        
        if result.decision:
            primary = result.decision.get("primary_action")
            if primary in ["escalate_to_human", "route_to_support"]:
                self._stats.escalated_to_human += 1
        
        if result.error:
            self._stats.errors += 1
    
    def reset_stats(self) -> None:
        """Reset processing statistics."""
        self._stats = ProcessingStats()
    
    def get_top_intents(self, limit: int = 5) -> List[tuple[str, int]]:
        """Get top intents by frequency.
        
        Args:
            limit: Maximum number of intents to return
            
        Returns:
            List of (intent, count) tuples
        """
        sorted_intents = sorted(
            self._stats.by_intent.items(),
            key=lambda x: -x[1]
        )
        return sorted_intents[:limit]
    
    def get_most_common_questions(self) -> List[Dict[str, Any]]:
        """Get the most common questions from processing logs.
        
        Returns:
            List of question data with counts
        """
        logs = self._engine.get_processing_logs(limit=500)
        
        questions = []
        for log in logs:
            if log.get("intent") == "question":
                questions.append({
                    "comment": log.get("comment"),
                    "count": 1,
                })
        
        # Aggregate similar questions
        question_map: Dict[str, int] = {}
        for q in questions:
            text = q.get("comment", "")[:50]  # Group by first 50 chars
            question_map[text] = question_map.get(text, 0) + 1
        
        return [
            {"question": q, "count": c}
            for q, c in sorted(question_map.items(), key=lambda x: -x[1])[:10]
        ]