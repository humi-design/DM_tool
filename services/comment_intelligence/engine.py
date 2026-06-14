"""Comment Intelligence Engine - Main orchestrator.

This module provides the central entry point for the Comment Intelligence
system, coordinating intent detection, knowledge retrieval, response
generation, and decision making.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
import asyncio
import time
import logging
from uuid import uuid4

from services.ai_provider.service import AIService
from services.comment_intelligence.intent import IntentDetector, IntentType, IntentResult
from services.comment_intelligence.context import ContextBuilder, CommentContext
from services.comment_intelligence.knowledge import KnowledgeBase, KnowledgeRetrievalResult
from services.comment_intelligence.generator import ResponseGenerator, ResponseOptions, GeneratedResponse
from services.comment_intelligence.decision import DecisionEngine, Decision, BusinessRules, ActionType
from services.comment_intelligence.emoji import EmojiMapper, EmojiReactionResult


@dataclass
class ProcessingResult:
    """Complete result of comment processing."""
    request_id: str
    comment_text: str
    author_username: Optional[str] = None
    
    # Intent detection
    intent: Optional[IntentType] = None
    intent_confidence: float = 0.0
    intent_reasoning: str = ""
    
    # Context
    context: Optional[Dict[str, Any]] = None
    
    # Knowledge
    knowledge_used: bool = False
    knowledge_entries_found: int = 0
    
    # Response
    response_content: Optional[str] = None
    follow_up_suggestion: Optional[str] = None
    
    # Decision
    decision: Optional[Dict[str, Any]] = None
    should_auto_reply: bool = False
    
    # Emoji processing
    emoji_reactions: List[Dict[str, Any]] = field(default_factory=list)
    
    # Processing metadata
    processing_time_ms: float = 0.0
    ai_result: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/API."""
        return {
            "request_id": self.request_id,
            "comment_text": self.comment_text,
            "author_username": self.author_username,
            "intent": self.intent.value if self.intent else None,
            "intent_confidence": self.intent_confidence,
            "intent_reasoning": self.intent_reasoning,
            "context": self.context,
            "knowledge_used": self.knowledge_used,
            "knowledge_entries_found": self.knowledge_entries_found,
            "response_content": self.response_content,
            "follow_up_suggestion": self.follow_up_suggestion,
            "decision": self.decision,
            "should_auto_reply": self.should_auto_reply,
            "emoji_reactions": self.emoji_reactions,
            "processing_time_ms": self.processing_time_ms,
            "ai_result": self.ai_result,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class EngineConfig:
    """Configuration for the Comment Intelligence Engine."""
    # AI Service settings
    ai_service: Optional[AIService] = None
    
    # Component settings
    enable_ai_fallback: bool = True
    enable_emoji_processing: bool = True
    enable_knowledge_retrieval: bool = True
    
    # Processing settings
    max_response_length: int = 500
    default_tone: str = "professional"
    min_confidence_for_auto_reply: float = 0.6
    
    # Business rules
    business_rules: Optional[BusinessRules] = None
    
    # Logging
    log_level: str = "INFO"


class CommentIntelligenceEngine:
    """Main engine for AI-powered comment intelligence.
    
    This class orchestrates the complete comment processing pipeline:
    1. Context Building - Gather relevant context
    2. Intent Detection - AI-powered semantic intent classification
    3. Knowledge Retrieval - Find relevant knowledge base entries
    4. Response Generation - Generate intelligent responses
    5. Decision Making - Route to appropriate actions
    6. Emoji Processing - Handle emoji reactions
    
    All components are configurable and support AI-powered fallbacks.
    """
    
    def __init__(self, config: Optional[EngineConfig] = None):
        """Initialize the engine.
        
        Args:
            config: Optional engine configuration
        """
        self._config = config or EngineConfig()
        self._logger = logging.getLogger("comment_intelligence")
        
        # Initialize components
        self._ai_service = self._config.ai_service
        self._intent_detector = IntentDetector(self._ai_service)
        self._context_builder = ContextBuilder()
        self._knowledge_base = KnowledgeBase()
        self._response_generator = ResponseGenerator(self._ai_service)
        self._decision_engine = DecisionEngine(self._config.business_rules)
        self._emoji_mapper = EmojiMapper()
        
        # Processing logs
        self._processing_logs: List[Dict[str, Any]] = []
        self._max_logs = 1000
    
    @property
    def ai_service(self) -> Optional[AIService]:
        """Get the AI service instance."""
        return self._ai_service
    
    @property
    def knowledge_base(self) -> KnowledgeBase:
        """Get the knowledge base instance."""
        return self._knowledge_base
    
    @property
    def decision_engine(self) -> DecisionEngine:
        """Get the decision engine instance."""
        return self._decision_engine
    
    @property
    def emoji_mapper(self) -> EmojiMapper:
        """Get the emoji mapper instance."""
        return self._emoji_mapper
    
    def configure_ai_service(self, ai_service: AIService) -> None:
        """Configure the AI service.
        
        Args:
            ai_service: AIService instance to use
        """
        self._ai_service = ai_service
        self._intent_detector = IntentDetector(ai_service)
        self._response_generator = ResponseGenerator(ai_service)
    
    async def process(
        self,
        comment_text: str,
        context: Optional[Dict[str, Any]] = None,
        author_username: Optional[str] = None,
        **kwargs
    ) -> ProcessingResult:
        """Process a single comment through the intelligence pipeline.
        
        Args:
            comment_text: The comment text to process
            context: Optional additional context
            author_username: Optional author username
            **kwargs: Additional processing parameters
            
        Returns:
            ProcessingResult with all processing details
        """
        request_id = str(uuid4())
        start_time = time.time()
        result = ProcessingResult(
            request_id=request_id,
            comment_text=comment_text,
            author_username=author_username,
        )
        
        try:
            # Step 1: Extract emojis if enabled
            if self._config.enable_emoji_processing:
                emojis = self._emoji_mapper.extract_emojis(comment_text)
                if emojis:
                    emoji_results = self._emoji_mapper.process_reactions(
                        emojis, 
                        {"author_username": author_username}
                    )
                    result.emoji_reactions = [
                        {
                            "emoji": r.emoji_used,
                            "reaction_intent": r.reaction_intent.value,
                            "mapped_intent": r.mapped_intent,
                            "response": r.response,
                        }
                        for r in emoji_results
                    ]
            
            # Step 2: Build context
            context_obj = await self._context_builder.build(
                comment_text=comment_text,
                author_username=author_username,
                **(context or {})
            )
            result.context = context_obj.to_dict()
            
            # Step 3: Detect intent
            intent_result = await self._intent_detector.detect(comment_text)
            result.intent = intent_result.intent
            result.intent_confidence = intent_result.confidence
            result.intent_reasoning = intent_result.reasoning
            
            # Update context with intent
            self._context_builder.enrich_with_intent(
                context_obj,
                intent_result.intent.value,
                intent_result.confidence
            )
            
            # Step 4: Knowledge retrieval
            knowledge_result: Optional[KnowledgeRetrievalResult] = None
            if self._config.enable_knowledge_retrieval:
                knowledge_result = self._knowledge_base.retrieve_for_intent(
                    intent_result.intent.value,
                    context=result.context,
                    limit=3
                )
                result.knowledge_used = len(knowledge_result.entries) > 0
                result.knowledge_entries_found = len(knowledge_result.entries)
            
            # Step 5: Generate response
            if self._config.enable_ai_fallback or self._ai_service:
                response_options = ResponseOptions(
                    max_length=self._config.max_response_length,
                    tone=self._config.default_tone,
                    follow_up_suggestion=True,
                )
                response_result = await self._response_generator.generate(
                    comment=comment_text,
                    intent=intent_result.intent.value,
                    context=context_obj,
                    knowledge=knowledge_result,
                    options=response_options,
                )
                result.response_content = response_result.content
                result.follow_up_suggestion = response_result.follow_up_suggestion
                result.ai_result = response_result.content
            
            # Step 6: Make decision
            decision = await self._decision_engine.decide(
                intent=intent_result.intent.value,
                confidence=intent_result.confidence,
                context=result.context,
            )
            result.decision = {
                "primary_action": decision.primary_action.value,
                "actions": [
                    {
                        "action_type": a.action_type.value,
                        "priority": a.priority,
                        "metadata": a.metadata,
                    }
                    for a in decision.actions
                ],
                "reasoning": decision.reasoning,
            }
            result.should_auto_reply = decision.should_auto_reply
            
            # Calculate processing time
            result.processing_time_ms = (time.time() - start_time) * 1000
            
            # Log the processing
            self._log_processing(result)
            
        except Exception as e:
            result.error = str(e)
            self._logger.error(f"Error processing comment: {e}")
        
        return result
    
    async def process_batch(
        self,
        comments: List[Dict[str, Any]],
    ) -> List[ProcessingResult]:
        """Process multiple comments in batch.
        
        Args:
            comments: List of dicts with 'text' and optional 'author', 'context'
            
        Returns:
            List of ProcessingResult for each comment
        """
        tasks = [
            self.process(
                comment_text=item["text"],
                context=item.get("context"),
                author_username=item.get("author"),
            )
            for item in comments
        ]
        return await asyncio.gather(*tasks)
    
    def _log_processing(self, result: ProcessingResult) -> None:
        """Log processing result.
        
        Args:
            result: ProcessingResult to log
        """
        log_entry = {
            "timestamp": result.timestamp.isoformat(),
            "request_id": result.request_id,
            "comment": result.comment_text[:100],  # Truncate for log
            "intent": result.intent.value if result.intent else None,
            "confidence": result.intent_confidence,
            "processing_time_ms": result.processing_time_ms,
            "error": result.error,
        }
        
        self._processing_logs.append(log_entry)
        
        # Trim logs if needed
        if len(self._processing_logs) > self._max_logs:
            self._processing_logs = self._processing_logs[-self._max_logs:]
    
    def get_processing_logs(
        self, 
        limit: int = 100,
        intent_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get recent processing logs.
        
        Args:
            limit: Maximum number of logs to return
            intent_filter: Optional intent type to filter by
            
        Returns:
            List of log entries
        """
        logs = self._processing_logs
        
        if intent_filter:
            logs = [l for l in logs if l.get("intent") == intent_filter]
        
        return logs[-limit:]
    
    def get_analytics(self) -> Dict[str, Any]:
        """Get analytics from processing logs.
        
        Returns:
            Dictionary with analytics data
        """
        if not self._processing_logs:
            return {
                "total_processed": 0,
                "intent_distribution": {},
                "average_confidence": 0.0,
                "average_processing_time_ms": 0.0,
            }
        
        # Calculate analytics
        total = len(self._processing_logs)
        
        # Intent distribution
        intent_counts: Dict[str, int] = {}
        total_confidence = 0.0
        total_time = 0.0
        errors = 0
        
        for log in self._processing_logs:
            intent = log.get("intent")
            if intent:
                intent_counts[intent] = intent_counts.get(intent, 0) + 1
            
            total_confidence += log.get("confidence", 0)
            total_time += log.get("processing_time_ms", 0)
            if log.get("error"):
                errors += 1
        
        return {
            "total_processed": total,
            "intent_distribution": intent_counts,
            "average_confidence": total_confidence / total if total > 0 else 0,
            "average_processing_time_ms": total_time / total if total > 0 else 0,
            "error_rate": errors / total if total > 0 else 0,
            "errors": errors,
        }
    
    def update_business_rules(self, rules: BusinessRules) -> None:
        """Update business rules for the decision engine.
        
        Args:
            rules: New BusinessRules to apply
        """
        self._decision_engine.update_rules(rules)
    
    def add_knowledge_entry(
        self,
        category: str,
        title: str,
        content: str,
        intent_types: List[str],
        keywords: Optional[List[str]] = None,
        priority: int = 5
    ) -> None:
        """Add a knowledge base entry.
        
        Args:
            category: Entry category
            title: Entry title
            content: Entry content
            intent_types: List of intent types this entry matches
            keywords: Optional list of keywords
            priority: Entry priority (higher = more relevant)
        """
        from services.comment_intelligence.knowledge import KnowledgeEntry
        
        entry = KnowledgeEntry(
            id=str(uuid4()),
            category=category,
            title=title,
            content=content,
            keywords=keywords or [],
            intent_types=intent_types,
            priority=priority,
        )
        self._knowledge_base.add_entry(entry)