"""Comment Intelligence Engine - AI-powered comment processing system.

This module provides semantic understanding and AI-driven processing
for Instagram comments with intent detection, knowledge retrieval,
and intelligent response generation.
"""

from services.comment_intelligence.engine import (
    CommentIntelligenceEngine,
    EngineConfig,
    ProcessingResult,
)
from services.comment_intelligence.intent import IntentType, IntentResult, IntentDetector
from services.comment_intelligence.context import ContextBuilder
from services.comment_intelligence.knowledge import KnowledgeBase
from services.comment_intelligence.generator import ResponseGenerator
from services.comment_intelligence.decision import DecisionEngine, ActionType
from services.comment_intelligence.processor import CommentProcessor
from services.comment_intelligence.emoji import EmojiMapper

__all__ = [
    "CommentIntelligenceEngine",
    "EngineConfig",
    "ProcessingResult",
    "IntentType",
    "IntentResult",
    "IntentDetector",
    "ContextBuilder",
    "KnowledgeBase",
    "ResponseGenerator",
    "DecisionEngine",
    "ActionType",
    "CommentProcessor",
    "EmojiMapper",
]