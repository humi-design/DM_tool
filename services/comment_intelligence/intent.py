"""Intent Detection Module - AI-powered semantic intent classification.

This module provides semantic understanding for comment classification
into intent categories with confidence scoring.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
import asyncio
import time

from services.ai_provider.base import Message, MessageRole
from services.ai_provider.service import AIService


class IntentType(Enum):
    """Supported intent types for comment classification."""
    GENERAL = "general"
    INTEREST = "interest"
    PRICE = "price"
    BOOKING = "booking"
    RESOURCE = "resource"
    SUPPORT = "support"
    QUESTION = "question"
    ORDER = "order"
    GREETING = "greeting"
    OTHER = "other"


@dataclass
class IntentResult:
    """Result of intent detection."""
    intent: IntentType
    confidence: float
    reasoning: str
    alternative_intents: List[tuple[IntentType, float]] = field(default_factory=list)
    entities: Dict[str, Any] = field(default_factory=dict)
    processing_time_ms: float = 0.0


class IntentDetector:
    """AI-powered intent detector using semantic understanding.
    
    This class uses AI to understand the true intent behind user comments,
    going beyond simple keyword matching to provide accurate classification
    with confidence scores.
    """
    
    SYSTEM_PROMPT = """You are an expert at understanding user intent in social media comments.
Your task is to classify incoming comments into one of these intent categories:

- GENERAL: General statements, opinions, or casual remarks
- INTEREST: User expressing interest in products/services
- PRICE: Questions or concerns about pricing, costs, or value
- BOOKING: Requests for appointments, reservations, or scheduling
- RESOURCE: Requests for information, brochures, PDFs, menus, guides
- SUPPORT: Questions about support, help, or troubleshooting
- QUESTION: Specific questions about features, specifications, or details
- ORDER: Requests to purchase, buy, or place orders
- GREETING: Greetings, hellos, or farewell messages
- OTHER: Anything that doesn't fit the above categories

Analyze the comment semantically, considering:
1. The actual meaning, not just keywords
2. Context and nuance in language
3. Implicit vs explicit requests
4. Cultural and conversational patterns

Return your analysis in JSON format with these fields:
- intent: The detected intent category
- confidence: A score from 0.0 to 1.0 indicating certainty
- reasoning: Brief explanation of why this intent was chosen
- alternative_intents: Other possible intents with their confidence scores
- entities: Any relevant entities extracted (prices, dates, product names, etc.)

Be honest about uncertainty - if the intent is unclear, indicate lower confidence."""

    INTENT_ANALYSIS_PROMPT = """Analyze this social media comment and determine the user's intent:

Comment: "{comment}"

Consider the full context and meaning. A short message like "Price?" or "Menu?" 
clearly indicates RESOURCE intent, not QUESTION. Emojis and reactions also
provide context about intent.

Return your analysis as a JSON object:
{{
    "intent": "INTENT_CATEGORY",
    "confidence": 0.0-1.0,
    "reasoning": "explanation of your analysis",
    "alternative_intents": [["INTENT", confidence], ...],
    "entities": {{"entity_type": "value", ...}}
}}"""

    def __init__(self, ai_service: Optional[AIService] = None):
        """Initialize the intent detector.
        
        Args:
            ai_service: Optional AIService instance for AI-powered detection.
                       If None, will use fallback keyword-based detection.
        """
        self._ai_service = ai_service
        self._fallback_enabled = ai_service is None
        
        # Fallback keyword patterns for when AI is unavailable
        self._intent_keywords = {
            IntentType.INTEREST: [
                "interested", "want", "need", "looking for", "love", "like", 
                "amazing", "beautiful", "perfect", "wish", "hope", "excited"
            ],
            IntentType.PRICE: [
                "price", "cost", "how much", "pricing", "expensive", "cheap",
                "afford", "budget", "discount", "deal", "sale", "worth"
            ],
            IntentType.BOOKING: [
                "book", "appointment", "schedule", "reserve", "reservation",
                "available", "time", "date", "slot", "booked", "booking"
            ],
            IntentType.RESOURCE: [
                "send", "share", "please", "menu", "brochure", "pdf", 
                "catalog", "info", "information", "details", "link", "website"
            ],
            IntentType.SUPPORT: [
                "help", "support", "problem", "issue", "broken", "not working",
                "frustrated", "angry", "complaint", "urgent", "asap"
            ],
            IntentType.QUESTION: [
                "what", "how", "why", "when", "where", "which", "can i",
                "do you", "is there", "are there", "?"
            ],
            IntentType.ORDER: [
                "buy", "order", "purchase", "checkout", "cart", "pay",
                "payment", "transaction", "shipping", "deliver"
            ],
            IntentType.GREETING: [
                "hi", "hello", "hey", "good morning", "good afternoon",
                "good evening", "thanks", "thank you", "bye", "goodbye"
            ],
        }
    
    @property
    def ai_available(self) -> bool:
        """Check if AI service is available."""
        return self._ai_service is not None and self._ai_service.is_initialized
    
    async def detect(self, comment: str) -> IntentResult:
        """Detect the intent of a comment using AI-powered semantic analysis.
        
        Args:
            comment: The comment text to analyze
            
        Returns:
            IntentResult with detected intent, confidence, and reasoning
        """
        start_time = time.time()
        
        if self.ai_available:
            try:
                return await self._detect_with_ai(comment)
            except Exception as e:
                # Fall back to keyword detection on AI failure
                pass
        
        # Fallback to keyword-based detection
        return self._detect_with_keywords(comment, start_time)
    
    async def _detect_with_ai(self, comment: str) -> IntentResult:
        """Detect intent using AI-powered semantic analysis."""
        conversation = self._ai_service.create_conversation(
            system_prompt=self.SYSTEM_PROMPT
        )
        
        prompt = self.INTENT_ANALYSIS_PROMPT.format(comment=comment)
        
        response = await self._ai_service.chat_with_conversation(
            conversation,
            prompt,
            temperature=0.3  # Lower temperature for more consistent classification
        )
        
        # Parse the AI response
        return self._parse_ai_response(response)
    
    def _parse_ai_response(self, response: str) -> IntentResult:
        """Parse AI response into IntentResult."""
        import json
        import re
        
        # Try to extract JSON from response
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if not json_match:
            # Try broader match
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
        
        if json_match:
            try:
                data = json.loads(json_match.group())
                
                intent_str = data.get("intent", "OTHER").upper()
                try:
                    intent = IntentType(intent_str.lower())
                except ValueError:
                    intent = IntentType.OTHER
                
                alternatives = data.get("alternative_intents", [])
                alt_list = []
                for alt in alternatives:
                    if isinstance(alt, list) and len(alt) >= 2:
                        try:
                            alt_intent = IntentType(alt[0].lower())
                            alt_list.append((alt_intent, float(alt[1])))
                        except (ValueError, TypeError):
                            continue
                
                return IntentResult(
                    intent=intent,
                    confidence=float(data.get("confidence", 0.5)),
                    reasoning=data.get("reasoning", "AI-generated analysis"),
                    alternative_intents=alt_list,
                    entities=data.get("entities", {}),
                    processing_time_ms=0.0  # Will be set by caller
                )
            except (json.JSONDecodeError, KeyError, TypeError):
                pass
        
        # Fallback: return OTHER with moderate confidence
        return IntentResult(
            intent=IntentType.OTHER,
            confidence=0.3,
            reasoning="Could not parse AI response, defaulting to OTHER",
            processing_time_ms=0.0
        )
    
    def _detect_with_keywords(self, comment: str, start_time: float) -> IntentResult:
        """Fallback keyword-based intent detection."""
        comment_lower = comment.lower()
        
        # Score each intent based on keyword matches
        scores: Dict[IntentType, float] = {}
        
        for intent, keywords in self._intent_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in comment_lower:
                    score += 1
            if score > 0:
                scores[intent] = score / len(keywords)
        
        if not scores:
            return IntentResult(
                intent=IntentType.GENERAL,
                confidence=0.5,
                reasoning="No specific intent keywords found, defaulting to GENERAL",
                processing_time_ms=(time.time() - start_time) * 1000
            )
        
        # Get the highest scoring intent
        best_intent = max(scores, key=scores.get)
        best_score = scores[best_intent]
        
        # Calculate confidence based on score and number of matches
        confidence = min(0.9, 0.4 + (best_score * 0.3))
        
        # Get alternative intents
        alternatives = [
            (intent, score) 
            for intent, score in sorted(scores.items(), key=lambda x: -x[1])
            if intent != best_intent and score > 0.2
        ]
        
        return IntentResult(
            intent=best_intent,
            confidence=confidence,
            reasoning=f"Keyword analysis found {len(scores)} potential intents, "
                     f"with {best_intent.value} being the strongest match",
            alternative_intents=alternatives[:3],
            processing_time_ms=(time.time() - start_time) * 1000
        )
    
    async def batch_detect(self, comments: List[str]) -> List[IntentResult]:
        """Detect intents for multiple comments.
        
        Args:
            comments: List of comment texts to analyze
            
        Returns:
            List of IntentResult for each comment
        """
        tasks = [self.detect(comment) for comment in comments]
        return await asyncio.gather(*tasks)