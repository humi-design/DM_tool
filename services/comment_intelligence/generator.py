"""AI Response Generator - Creates intelligent, context-aware responses.

This module uses AI to generate natural, engaging responses to comments
based on intent, context, and knowledge base information.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
import asyncio
import time
import json

from services.ai_provider.base import Message, MessageRole
from services.ai_provider.service import AIService
from services.comment_intelligence.context import CommentContext
from services.comment_intelligence.knowledge import KnowledgeRetrievalResult


@dataclass
class ResponseOptions:
    """Options for response generation."""
    max_length: int = 500
    tone: str = "professional"  # professional, friendly, casual, formal
    include_emoji: bool = True
    personalize: bool = True
    temperature: float = 0.7
    follow_up_suggestion: bool = True


@dataclass
class GeneratedResponse:
    """A generated response with metadata."""
    content: str
    intent: str
    confidence: float
    context_used: bool
    knowledge_used: bool
    processing_time_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    follow_up_suggestion: Optional[str] = None


class ResponseGenerator:
    """AI-powered response generator for comments.
    
    This class generates intelligent, context-aware responses using
    AI capabilities with knowledge base augmentation.
    """
    
    SYSTEM_PROMPT = """You are an expert social media manager for businesses on Instagram.
Your role is to generate engaging, helpful, and brand-appropriate responses to customer comments.

Guidelines for responses:
1. Be friendly, helpful, and professional
2. Address the user's specific question or need
3. Keep responses concise but informative (aim for 1-3 sentences)
4. Use a conversational tone that matches the brand
5. When appropriate, offer to help further or suggest next steps
6. Never make promises about pricing, availability, or delivery
7. If you don't know something, offer to connect them with someone who can help
8. Include relevant emojis sparingly to add personality (optional based on context)

Response tone options:
- professional: Clean, business-focused responses
- friendly: Warm, approachable responses  
- casual: Relaxed, informal responses
- formal: Polished, formal responses

You will be provided with:
- The user's comment
- Context about the business and user
- Detected intent and confidence
- Relevant knowledge base information

Generate a response that addresses the user's needs appropriately."""

    TONE_INSTRUCTIONS = {
        "professional": "Use a professional tone. Be clear and concise.",
        "friendly": "Use a friendly, warm tone. Show genuine enthusiasm.",
        "casual": "Use casual language. Feel free to be playful.",
        "formal": "Use formal language. Be precise and courteous.",
    }

    def __init__(self, ai_service: Optional[AIService] = None):
        """Initialize the response generator.
        
        Args:
            ai_service: Optional AIService for AI-powered generation
        """
        self._ai_service = ai_service
        self._fallback_templates = self._load_fallback_templates()
    
    def _load_fallback_templates(self) -> Dict[str, List[str]]:
        """Load fallback response templates for when AI is unavailable."""
        return {
            "interest": [
                "Thanks for your interest! We'd love to tell you more.",
                "Great to hear from you! Let us know if you have any questions.",
            ],
            "price": [
                "For pricing details, please visit our website or DM us.",
                "Prices vary by product. Would you like a personalized quote?",
            ],
            "booking": [
                "We'd be happy to help you book! What time works for you?",
                "Let us know your preferred date and time.",
            ],
            "resource": [
                "Happy to share more info! What's the best way to reach you?",
                "I'll send you the details shortly!",
            ],
            "support": [
                "We're here to help! Could you provide more details?",
                "Let me look into this for you. Can you share more information?",
            ],
            "question": [
                "Great question! Here's what you need to know...",
                "Thanks for asking! Let me share some details...",
            ],
            "order": [
                "You can place an order through our website. Need help?",
                "I'll guide you through the ordering process!",
            ],
            "greeting": [
                "Hello! Thanks for reaching out!",
                "Hi there! How can we help you today?",
            ],
            "general": [
                "Thanks for your comment!",
                "We appreciate you reaching out!",
            ],
            "other": [
                "Thanks for sharing! Let us know if you need anything.",
                "We appreciate your input!",
            ],
        }
    
    @property
    def ai_available(self) -> bool:
        """Check if AI service is available."""
        return self._ai_service is not None and self._ai_service.is_initialized
    
    async def generate(
        self,
        comment: str,
        intent: str,
        context: Optional[CommentContext] = None,
        knowledge: Optional[KnowledgeRetrievalResult] = None,
        options: Optional[ResponseOptions] = None
    ) -> GeneratedResponse:
        """Generate a response for the given comment.
        
        Args:
            comment: The original comment
            intent: Detected intent type
            context: Optional comment context
            knowledge: Optional knowledge retrieval results
            options: Optional response generation options
            
        Returns:
            GeneratedResponse with content and metadata
        """
        start_time = time.time()
        options = options or ResponseOptions()
        
        if self.ai_available:
            try:
                return await self._generate_with_ai(comment, intent, context, knowledge, options)
            except Exception:
                pass
        
        # Fallback to template-based response
        return self._generate_with_template(comment, intent, context, options, start_time)
    
    async def _generate_with_ai(
        self,
        comment: str,
        intent: str,
        context: Optional[CommentContext],
        knowledge: Optional[KnowledgeRetrievalResult],
        options: ResponseOptions
    ) -> GeneratedResponse:
        """Generate response using AI."""
        conversation = self._ai_service.create_conversation(
            system_prompt=self.SYSTEM_PROMPT
        )
        
        # Build prompt with context
        prompt_parts = []
        
        # Tone instruction
        prompt_parts.append(f"Tone: {options.tone}")
        prompt_parts.append(f"Tone instruction: {self.TONE_INSTRUCTIONS.get(options.tone, '')}")
        
        # Comment info
        prompt_parts.append(f"\nUser's Comment: \"{comment}\"")
        prompt_parts.append(f"Detected Intent: {intent}")
        
        # Context
        if context:
            prompt_parts.append(f"\nContext:\n{context.to_prompt_context()}")
        
        # Knowledge base info
        if knowledge and knowledge.entries:
            prompt_parts.append(f"\n{knowledge.to_context_string()}")
        
        # Response constraints
        prompt_parts.append(f"\nMax response length: {options.max_length} characters")
        if options.include_emoji:
            prompt_parts.append("You may use relevant emojis if appropriate.")
        else:
            prompt_parts.append("Do not use emojis.")
        
        # Follow-up suggestion request
        if options.follow_up_suggestion:
            prompt_parts.append("\nAlso suggest a brief follow-up action or question (prefix with 'Follow-up:').")
        
        prompt = "\n".join(prompt_parts)
        
        response_text = await self._ai_service.chat_with_conversation(
            conversation,
            prompt,
            temperature=options.temperature
        )
        
        # Parse response and extract follow-up suggestion
        follow_up = None
        if options.follow_up_suggestion and "Follow-up:" in response_text:
            parts = response_text.split("Follow-up:")
            response_text = parts[0].strip()
            follow_up = parts[1].strip() if len(parts) > 1 else None
        
        processing_time = (time.time() - start_time) * 1000
        
        return GeneratedResponse(
            content=response_text[:options.max_length],
            intent=intent,
            confidence=0.8,  # AI response assumed higher confidence
            context_used=context is not None,
            knowledge_used=knowledge is not None and len(knowledge.entries) > 0,
            processing_time_ms=processing_time,
            metadata={"ai_generated": True},
            follow_up_suggestion=follow_up
        )
    
    def _generate_with_template(
        self,
        comment: str,
        intent: str,
        context: Optional[CommentContext],
        options: ResponseOptions,
        start_time: float
    ) -> GeneratedResponse:
        """Generate response using templates (fallback when AI unavailable)."""
        import random
        
        templates = self._fallback_templates.get(intent, self._fallback_templates["other"])
        base_response = random.choice(templates)
        
        # Personalize if possible
        response = base_response
        if context and context.author_username:
            response = response.replace("!", f", @{context.author_username}!")
        
        # Add emoji if enabled
        if options.include_emoji:
            emoji = self._get_intent_emoji(intent)
            if emoji:
                response = f"{response} {emoji}"
        
        processing_time = (time.time() - start_time) * 1000
        
        return GeneratedResponse(
            content=response,
            intent=intent,
            confidence=0.5,  # Lower confidence for template-based
            context_used=context is not None,
            knowledge_used=False,
            processing_time_ms=processing_time,
            metadata={"ai_generated": False, "fallback": True}
        )
    
    def _get_intent_emoji(self, intent: str) -> str:
        """Get an emoji appropriate for an intent."""
        emoji_map = {
            "interest": "😊",
            "price": "💰",
            "booking": "📅",
            "resource": "📋",
            "support": "🤝",
            "question": "❓",
            "order": "🛒",
            "greeting": "👋",
            "general": "✨",
            "other": "💬",
        }
        return emoji_map.get(intent.lower(), "")
    
    async def batch_generate(
        self,
        items: List[Dict[str, Any]],
        options: Optional[ResponseOptions] = None
    ) -> List[GeneratedResponse]:
        """Generate responses for multiple comments.
        
        Args:
            items: List of dicts with 'comment', 'intent', optional 'context' and 'knowledge'
            options: Optional response generation options
            
        Returns:
            List of GeneratedResponse for each item
        """
        tasks = [
            self.generate(
                item["comment"],
                item["intent"],
                item.get("context"),
                item.get("knowledge"),
                options
            )
            for item in items
        ]
        return await asyncio.gather(*tasks)