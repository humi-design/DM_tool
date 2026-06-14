"""Decision Engine Module - Routes processing based on intent and context.

This module makes intelligent routing decisions about how to handle
comments based on detected intent, confidence, and business rules.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Callable
import asyncio


class ActionType(Enum):
    """Types of actions that can be taken for comments."""
    AUTO_REPLY = "auto_reply"
    FLAG_FOR_REVIEW = "flag_for_review"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    LOG_ONLY = "log_only"
    IGNORE = "ignore"
    ROUTE_TO_SUPPORT = "route_to_support"
    ROUTE_TO_SALES = "route_to_sales"
    TRIGGER_WORKFLOW = "trigger_workflow"
    STORE_LEAD = "store_lead"
    SEND_RESOURCE = "send_resource"


@dataclass
class Action:
    """A single action to be taken."""
    action_type: ActionType
    priority: int = 0
    response_content: Optional[str] = None
    target_queue: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence_threshold: float = 0.0
    conditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Decision:
    """Result of a decision made by the engine."""
    actions: List[Action]
    primary_action: ActionType
    confidence: float
    reasoning: str
    should_auto_reply: bool
    should_respond_immediately: bool
    processing_hints: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BusinessRules:
    """Configurable business rules for decision making."""
    # Confidence thresholds
    high_confidence_threshold: float = 0.8
    medium_confidence_threshold: float = 0.5
    low_confidence_threshold: float = 0.3
    
    # Auto-reply settings
    auto_reply_enabled: bool = True
    auto_reply_intents: List[str] = field(default_factory=lambda: [
        "interest", "greeting", "question", "resource"
    ])
    auto_reply_min_confidence: float = 0.6
    
    # Escalation settings
    auto_escalate_support: bool = True
    auto_escalate_complaints: bool = True
    auto_escalate_urgent: bool = True
    escalate_on_low_confidence: bool = True
    
    # Lead capture settings
    capture_leads: bool = True
    lead_intents: List[str] = field(default_factory=lambda: [
        "interest", "price", "booking", "order"
    ])
    
    # Spam/profanity handling
    flag_spam: bool = True
    flag_profanity: bool = True
    
    # Review settings
    flag_for_review_intents: List[str] = field(default_factory=lambda: [
        "support", "complaint"
    ])
    flag_for_review_low_confidence: bool = True


class DecisionEngine:
    """AI-powered decision engine for comment routing.
    
    This class makes intelligent decisions about how to handle comments
    based on detected intent, confidence scores, and configurable business rules.
    """
    
    def __init__(self, rules: Optional[BusinessRules] = None):
        """Initialize the decision engine.
        
        Args:
            rules: Optional custom business rules
        """
        self._rules = rules or BusinessRules()
        self._custom_handlers: Dict[str, Callable] = {}
        self._workflows: Dict[str, Dict[str, Any]] = {}
    
    @property
    def rules(self) -> BusinessRules:
        """Get current business rules."""
        return self._rules
    
    def update_rules(self, rules: BusinessRules) -> None:
        """Update business rules.
        
        Args:
            rules: New business rules to apply
        """
        self._rules = rules
    
    def register_handler(self, name: str, handler: Callable) -> None:
        """Register a custom decision handler.
        
        Args:
            name: Handler name
            handler: Callable that takes context and returns Decision
        """
        self._custom_handlers[name] = handler
    
    def register_workflow(self, name: str, workflow: Dict[str, Any]) -> None:
        """Register a workflow trigger.
        
        Args:
            name: Workflow name
            workflow: Workflow configuration
        """
        self._workflows[name] = workflow
    
    async def decide(
        self,
        intent: str,
        confidence: float,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Decision:
        """Make a routing decision for a comment.
        
        Args:
            intent: Detected intent type
            confidence: Detection confidence score
            context: Optional processing context
            **kwargs: Additional decision parameters
            
        Returns:
            Decision with actions to take
        """
        context = context or {}
        actions: List[Action] = []
        reasoning_parts = []
        
        # Determine confidence level
        if confidence >= self._rules.high_confidence_threshold:
            confidence_level = "high"
        elif confidence >= self._rules.medium_confidence_threshold:
            confidence_level = "medium"
        else:
            confidence_level = "low"
        
        reasoning_parts.append(f"Intent '{intent}' detected with {confidence_level} confidence ({confidence:.2f})")
        
        # Check for escalation triggers
        should_escalate = self._should_escalate(intent, confidence, context)
        if should_escalate:
            actions.append(Action(
                action_type=ActionType.ESCALATE_TO_HUMAN,
                priority=100,
                metadata={"escalation_reason": "configured_rule"},
                confidence_threshold=self._rules.medium_confidence_threshold
            ))
            reasoning_parts.append("Escalating to human review")
        
        # Check for lead capture
        if self._rules.capture_leads and intent in self._rules.lead_intents:
            actions.append(Action(
                action_type=ActionType.STORE_LEAD,
                priority=80,
                metadata={"lead_source": "comment", "intent": intent}
            ))
            reasoning_parts.append("Capturing as lead")
        
        # Determine auto-reply eligibility
        should_auto_reply = (
            self._rules.auto_reply_enabled and
            intent in self._rules.auto_reply_intents and
            confidence >= self._rules.auto_reply_min_confidence
        )
        
        if should_auto_reply:
            actions.append(Action(
                action_type=ActionType.AUTO_REPLY,
                priority=50,
                conditions={"min_confidence": self._rules.auto_reply_min_confidence}
            ))
            reasoning_parts.append("Eligible for auto-reply")
        
        # Check for review flags
        if self._should_flag_for_review(intent, confidence, context):
            actions.append(Action(
                action_type=ActionType.FLAG_FOR_REVIEW,
                priority=70,
                metadata={"flag_reason": "configured_rule"}
            ))
            reasoning_parts.append("Flagged for review")
        
        # Check for support routing
        if intent == "support":
            actions.append(Action(
                action_type=ActionType.ROUTE_TO_SUPPORT,
                priority=90,
                target_queue="support"
            ))
            reasoning_parts.append("Routing to support queue")
        
        # Check for sales routing
        if intent in ["interest", "price", "order", "booking"]:
            actions.append(Action(
                action_type=ActionType.ROUTE_TO_SALES,
                priority=85,
                target_queue="sales"
            ))
            reasoning_parts.append("Routing to sales queue")
        
        # Check for resource sending
        if intent == "resource":
            actions.append(Action(
                action_type=ActionType.SEND_RESOURCE,
                priority=60,
                metadata={"resource_type": context.get("resource_type", "general")}
            ))
            reasoning_parts.append("Sending requested resource")
        
        # Default: log only if no other actions
        if not actions:
            actions.append(Action(
                action_type=ActionType.LOG_ONLY,
                priority=10
            ))
            reasoning_parts.append("No specific action required, logging only")
        
        # Sort actions by priority
        actions.sort(key=lambda a: -a.priority)
        
        # Determine primary action
        primary_action = actions[0].action_type if actions else ActionType.LOG_ONLY
        
        # Should respond immediately if auto-reply is primary
        should_respond_immediately = primary_action == ActionType.AUTO_REPLY
        
        return Decision(
            actions=actions,
            primary_action=primary_action,
            confidence=confidence,
            reasoning="; ".join(reasoning_parts),
            should_auto_reply=should_auto_reply,
            should_respond_immediately=should_respond_immediately,
            processing_hints=self._get_processing_hints(intent, context),
            metadata={
                "confidence_level": confidence_level,
                "intent": intent,
                "rules_applied": True
            }
        )
    
    def _should_escalate(
        self,
        intent: str,
        confidence: float,
        context: Dict[str, Any]
    ) -> bool:
        """Determine if a comment should be escalated."""
        # Always escalate low confidence if configured
        if self._rules.escalate_on_low_confidence and confidence < self._rules.low_confidence_threshold:
            return True
        
        # Escalate support issues
        if self._rules.auto_escalate_support and intent == "support":
            return True
        
        # Escalate complaints
        if self._rules.auto_escalate_complaints and context.get("is_complaint"):
            return True
        
        # Escalate urgent messages
        if self._rules.auto_escalate_urgent and context.get("is_urgent"):
            return True
        
        # Escalate negative sentiment
        if context.get("sentiment_score", 0) < -0.5:
            return True
        
        return False
    
    def _should_flag_for_review(
        self,
        intent: str,
        confidence: float,
        context: Dict[str, Any]
    ) -> bool:
        """Determine if a comment should be flagged for review."""
        # Flag specific intents
        if intent in self._rules.flag_for_review_intents:
            return True
        
        # Flag low confidence if configured
        if self._rules.flag_for_review_low_confidence and confidence < self._rules.medium_confidence_threshold:
            return True
        
        # Flag potential spam
        if self._rules.flag_spam and context.get("is_spam"):
            return True
        
        # Flag profanity
        if self._rules.flag_profanity and context.get("has_profanity"):
            return True
        
        return False
    
    def _get_processing_hints(
        self,
        intent: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get processing hints based on intent and context."""
        hints = {
            "tone": "professional",
            "response_style": "concise",
        }
        
        if intent == "greeting":
            hints["tone"] = "friendly"
            hints["response_style"] = "brief"
        elif intent == "support":
            hints["tone"] = "empathetic"
            hints["response_style"] = "detailed"
        elif intent == "interest":
            hints["tone"] = "enthusiastic"
            hints["response_style"] = "engaging"
        elif intent == "price":
            hints["tone"] = "professional"
            hints["response_style"] = "informative"
        
        return hints
    
    async def batch_decide(
        self,
        items: List[Dict[str, Any]]
    ) -> List[Decision]:
        """Make decisions for multiple comments.
        
        Args:
            items: List of dicts with 'intent', 'confidence', and optional 'context'
            
        Returns:
            List of Decision for each item
        """
        tasks = [
            self.decide(
                item["intent"],
                item["confidence"],
                item.get("context")
            )
            for item in items
        ]
        return await asyncio.gather(*tasks)
    
    def validate_rules(self) -> List[str]:
        """Validate current business rules.
        
        Returns:
            List of validation warnings/errors
        """
        issues = []
        
        if self._rules.auto_reply_min_confidence < 0 or self._rules.auto_reply_min_confidence > 1:
            issues.append("auto_reply_min_confidence must be between 0 and 1")
        
        if self._rules.high_confidence_threshold < self._rules.medium_confidence_threshold:
            issues.append("high_confidence_threshold should be >= medium_confidence_threshold")
        
        if self._rules.medium_confidence_threshold < self._rules.low_confidence_threshold:
            issues.append("medium_confidence_threshold should be >= low_confidence_threshold")
        
        return issues