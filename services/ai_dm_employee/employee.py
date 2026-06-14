"""AI DM Employee - Main orchestration class for professional customer success AI agent."""

import asyncio
import uuid
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable, Awaitable
from enum import Enum

from services.ai_dm_employee.conversation_memory import ConversationMemoryManager
from services.ai_dm_employee.business_context import BusinessContextManager, BusinessContext
from services.ai_dm_employee.knowledge_base import KnowledgeBaseService, DocumentType
from services.ai_dm_employee.safety import SafetyValidator, SafetyResult
from services.ai_dm_employee.moderation import ModerationLayer, ModerationLevel, ModerationResult
from services.ai_dm_employee.hallucination_prevention import (
    HallucinationPrevention,
    HallucinationCheck,
    ConfidenceLevel,
)
from services.ai_dm_employee.logging_service import AIDMLoggingService, LogLevel, LogCategory


class DMEmployeeStatus(Enum):
    """Status of the AI DM Employee."""
    READY = "ready"
    PROCESSING = "processing"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


@dataclass
class ProcessingResult:
    """Result of processing a message."""
    success: bool
    response: str
    confidence: float = 1.0
    requires_human: bool = False
    should_send: bool = True
    intent: Optional[str] = None
    entities: Dict[str, Any] = field(default_factory=dict)
    resources_recommended: List[Dict[str, str]] = field(default_factory=list)
    follow_up_suggestions: List[str] = field(default_factory=list)
    safety_result: Optional[SafetyResult] = None
    hallucination_result: Optional[HallucinationCheck] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    processing_time_ms: float = 0.0


class AIDMEmployee:
    """AI DM Employee - Professional Customer Success AI Agent.
    
    Architecture:
    1. Incoming Message
    2. Conversation Memory
    3. Business Context
    4. Knowledge Base
    5. AI Processing
    6. Safety Validation
    7. Moderation
    8. Hallucination Prevention
    9. Response
    10. Conversation Storage
    
    Features:
    - Natural conversations with context awareness
    - Resource recommendations
    - Appointment suggestions
    - Lead qualification
    - Question answering
    - Human takeover capability
    - Conversation history
    - Typing indicator abstraction
    - Multi-provider support (Gemini, OpenAI, Claude, Ollama, etc.)
    """
    
    def __init__(
        self,
        business_id: str,
        business_context: BusinessContext,
        ai_provider_manager,
        config: Optional[Dict[str, Any]] = None,
        log_dir: Optional[str] = None,
    ):
        """Initialize the AI DM Employee.
        
        Args:
            business_id: Business identifier
            business_context: Business context data
            ai_provider_manager: AI provider manager instance
            config: Optional configuration dictionary
            log_dir: Optional directory for log persistence
        """
        self.business_id = business_id
        self.business_context = business_context
        
        # Core components
        self.conversation_memory = ConversationMemoryManager()
        self.business_context_manager = BusinessContextManager()
        self.knowledge_base = KnowledgeBaseService()
        self.safety_validator = SafetyValidator()
        self.moderation_layer = ModerationLayer(level=ModerationLevel.STANDARD)
        self.hallucination_prevention = HallucinationPrevention()
        self.logging_service = AIDMLoggingService(log_dir=log_dir)
        
        # AI Provider
        self.ai_provider_manager = ai_provider_manager
        
        # Configuration
        self.config = config or {}
        self.status = DMEmployeeStatus.READY
        
        # Human takeover callback
        self.human_takeover_callback: Optional[Callable] = None
        
        # Load business context
        self._load_business_context()
        
        # Initialize hallucination prevention with knowledge base
        self.hallucination_prevention.set_knowledge_base(self.knowledge_base)
    
    def _load_business_context(self) -> None:
        """Load business context into all components."""
        # Add to business context manager
        context_data = {
            "name": self.business_context.business_name,
            "business_type": self.business_context.business_type,
            "industry": self.business_context.industry,
            "description": self.business_context.description,
            "website": self.business_context.website,
            "email": self.business_context.email,
            "phone": self.business_context.phone,
            "address": self.business_context.address,
            "products": [p for p in self.business_context.products],
            "services": [s for s in self.business_context.services],
            "faq": [f for f in self.business_context.faq],
            "policies": dict(self.business_context.policies),
            "ai_personality": self.business_context.ai_personality,
            "ai_tone": self.business_context.ai_tone,
        }
        
        self.business_context_manager.create_context_from_dict(
            business_id=self.business_id,
            data=context_data,
        )
        
        # Index FAQ
        if self.business_context.faq:
            self.knowledge_base.index_faq(self.business_id, self.business_context.faq)
        
        # Index products
        if self.business_context.products:
            self.knowledge_base.index_products(self.business_id, self.business_context.products)
        
        # Index services
        if self.business_context.services:
            for service in self.business_context.services:
                self.knowledge_base.index_document(
                    business_id=self.business_id,
                    content=f"Service: {service.get('name', '')}\n{ service.get('description', '')}",
                    doc_type=DocumentType.SERVICE,
                    title=service.get("name", ""),
                    tags=["service"],
                )
    
    def set_human_takeover_callback(
        self,
        callback: Callable[[str, str, str], Awaitable[None]],
    ) -> None:
        """Set callback for human takeover requests.
        
        Args:
            callback: Async function(conversation_id, reason, message) to handle takeover
        """
        self.human_takeover_callback = callback
    
    async def process_message(
        self,
        conversation_id: str,
        user_id: str,
        username: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ProcessingResult:
        """Process an incoming message and generate a response.
        
        Pipeline:
        1. Validate input
        2. Load conversation memory
        3. Load business context
        4. Retrieve relevant knowledge
        5. Generate AI response
        6. Validate safety
        7. Apply moderation
        8. Check for hallucinations
        9. Return response
        
        Args:
            conversation_id: Conversation identifier
            user_id: User identifier
            username: Instagram username
            message: Incoming message
            context: Optional additional context
            
        Returns:
            ProcessingResult with response and metadata
        """
        start_time = datetime.utcnow()
        request_id = str(uuid.uuid4())
        
        self.status = DMEmployeeStatus.PROCESSING
        
        # Initialize conversation context
        conv_context = self.conversation_memory.get_or_create_context(
            conversation_id=conversation_id,
            participant_id=user_id,
            participant_username=username,
        )
        
        # Load business context into conversation
        if not conv_context.business_context_loaded:
            bc = self.business_context_manager.get_context(self.business_id)
            if bc:
                bc_dict = {
                    "name": bc.business_name,
                    "description": bc.description,
                    "website": bc.website,
                }
                self.conversation_memory.set_business_context(conversation_id, bc_dict)
        
        # Log incoming message
        self.logging_service.start_session(
            conversation_id=conversation_id,
            business_id=self.business_id,
            user_id=user_id,
        )
        self.logging_service.log_message_received(
            conversation_id=conversation_id,
            business_id=self.business_id,
            message=message,
            user_id=user_id,
        )
        
        try:
            # Step 1: Safety check on input
            safety_result = self.safety_validator.validate_input(message, context)
            
            if not safety_result.is_safe:
                self.logging_service.log_safety_check(
                    conversation_id=conversation_id,
                    business_id=self.business_id,
                    passed=False,
                    concerns=[c[2] for c in safety_result.concerns],
                )
                
                return ProcessingResult(
                    success=False,
                    response="I appreciate your message, but I need to flag this for review.",
                    confidence=0.0,
                    requires_human=True,
                    safety_result=safety_result,
                    metadata={"blocked": True},
                    processing_time_ms=self._calc_time_ms(start_time),
                )
            
            # Step 2: Add message to conversation memory
            self.conversation_memory.add_message(
                conversation_id=conversation_id,
                role="user",
                content=message,
            )
            
            # Step 3: Detect intent and entities
            intent, entities = self._detect_intent(message)
            
            # Step 4: Retrieve relevant knowledge
            relevant_context = self.knowledge_base.get_relevant_context(
                business_id=self.business_id,
                query=message,
                max_chars=1500,
            )
            
            # Check FAQ
            faq_answer = self.business_context_manager.find_faq_answer(
                business_id=self.business_id,
                question=message,
            )
            
            # Step 5: Build prompt
            prompt = self._build_prompt(
                conversation_id=conversation_id,
                user_message=message,
                intent=intent,
                entities=entities,
                knowledge_context=relevant_context,
                faq_answer=faq_answer,
            )
            
            # Step 6: Generate AI response
            ai_response = await self._generate_response(prompt, request_id)
            
            if not ai_response:
                return ProcessingResult(
                    success=False,
                    response="I apologize, but I'm having trouble generating a response right now. A human will follow up shortly.",
                    confidence=0.0,
                    requires_human=True,
                    error="AI generation failed",
                    metadata={"fallback": True},
                    processing_time_ms=self._calc_time_ms(start_time),
                )
            
            # Step 7: Safety check on output
            output_safety = self.safety_validator.validate_output(ai_response, context)
            
            if not output_safety.is_safe:
                self.logging_service.log_safety_check(
                    conversation_id=conversation_id,
                    business_id=self.business_id,
                    passed=False,
                    concerns=[c[2] for c in output_safety.concerns],
                )
                
                return ProcessingResult(
                    success=False,
                    response="I apologize, but I need to review this before responding.",
                    confidence=0.0,
                    requires_human=True,
                    safety_result=output_safety,
                    processing_time_ms=self._calc_time_ms(start_time),
                )
            
            # Step 8: Apply moderation
            moderation_result = self.moderation_layer.moderate(ai_response, context)
            
            final_response = moderation_result.sanitized_content or ai_response
            
            # Step 9: Hallucination check
            hallucination_result = self.hallucination_prevention.check_response(
                response=final_response,
                business_id=self.business_id,
                user_query=message,
            )
            
            # Handle low confidence responses
            if hallucination_result.confidence == ConfidenceLevel.UNVERIFIABLE:
                final_response = self.hallucination_prevention.get_safe_alternative(
                    response=final_response,
                    check=hallucination_result,
                    user_query=message,
                )
            
            # Step 10: Determine follow-up and resources
            follow_ups = self._generate_follow_ups(intent, entities)
            resources = self._recommend_resources(intent, entities)
            
            # Add response to memory
            self.conversation_memory.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=final_response,
                metadata={
                    "intent": intent,
                    "confidence": hallucination_result.score,
                },
            )
            
            # Update lead status based on intent
            if intent in ["purchase_intent", "pricing_inquiry"]:
                self.conversation_memory.update_lead_status(
                    conversation_id=conversation_id,
                    status="interested",
                    score=conv_context.lead_score + 10,
                )
            
            # Check for human takeover conditions
            requires_human = self._should_request_human_takeover(
                conversation_id=conversation_id,
                intent=intent,
                confidence=hallucination_result.score,
            )
            
            if requires_human:
                self.conversation_memory.request_human_takeover(
                    conversation_id=conversation_id,
                    reason=f"Low confidence ({hallucination_result.score:.2f}) and {intent} intent",
                )
                self.logging_service.log_human_takeover(
                    conversation_id=conversation_id,
                    business_id=self.business_id,
                    reason=f"Intent: {intent}, Confidence: {hallucination_result.score}",
                )
                
                # Notify via callback if set
                if self.human_takeover_callback:
                    await self.human_takeover_callback(
                        conversation_id,
                        f"Low confidence response: {intent}",
                        final_response,
                    )
            
            processing_time = self._calc_time_ms(start_time)
            
            # Log success
            self.logging_service.log(
                level=LogLevel.INFO,
                category=LogCategory.MESSAGE_PROCESSING,
                message="Message processed successfully",
                conversation_id=conversation_id,
                business_id=self.business_id,
                duration_ms=processing_time,
                data={
                    "intent": intent,
                    "confidence": hallucination_result.score,
                    "requires_human": requires_human,
                },
            )
            
            self.status = DMEmployeeStatus.READY
            
            return ProcessingResult(
                success=True,
                response=final_response,
                confidence=hallucination_result.score,
                requires_human=requires_human,
                should_send=not requires_human,
                intent=intent,
                entities=entities,
                resources_recommended=resources,
                follow_up_suggestions=follow_ups,
                safety_result=safety_result,
                hallucination_result=hallucination_result,
                metadata={
                    "moderation_passed": moderation_result.is_approved,
                    "request_id": request_id,
                },
                processing_time_ms=processing_time,
            )
            
        except Exception as e:
            self.status = DMEmployeeStatus.ERROR
            
            self.logging_service.log_error(
                conversation_id=conversation_id,
                business_id=self.business_id,
                error=str(e),
                stack_trace=None,
            )
            
            return ProcessingResult(
                success=False,
                response="I apologize, but I encountered an error processing your message. A human will follow up shortly.",
                confidence=0.0,
                requires_human=True,
                error=str(e),
                processing_time_ms=self._calc_time_ms(start_time),
            )
    
    def _detect_intent(
        self,
        message: str,
    ) -> tuple[str, Dict[str, Any]]:
        """Detect user intent from message.
        
        Args:
            message: User message
            
        Returns:
            Tuple of (intent, entities)
        """
        message_lower = message.lower()
        entities = {}
        
        # Intent patterns
        intents = {
            "greeting": [
                r'\b(hi|hello|hey|good morning|good afternoon|good evening|howdy)\b',
            ],
            "pricing_inquiry": [
                r'\b(price|cost|how much|expense|fee|charge|quote|estimate|budget)\b',
            ],
            "purchase_intent": [
                r'\b(buy|purchase|order|get|want|need|interested|inquire)\b.*\b(now|today|this)\b',
                r'\b(how (do|can) i (order|buy|purchase))\b',
            ],
            "product_inquiry": [
                r'\b(product|item|what.*offer|available|selection|catalog)\b',
            ],
            "service_inquiry": [
                r'\b(service|help|assistance|support|what.*do|can.*help)\b',
            ],
            "appointment_request": [
                r'\b(appointment|schedule|book|reserve|meeting|consultation|call)\b',
            ],
            "faq": [
                r'\b(where|when|what|who|why|how|is.*it|do.*you|can.*i|hours|location|address)\b',
            ],
            "complaint": [
                r'\b(problem|issue|wrong|disappointed|frustrated|angry|not happy|complaint)\b',
            ],
            "feedback": [
                r'\b(feedback|review|opinion|suggestion|recommend)\b',
            ],
            "goodbye": [
                r'\b(bye|goodbye|thanks?|thank you|that\'s all|that\'s it)\b',
            ],
            "human_request": [
                r'\b(human|agent|real person|person|representative|speak.*someone)\b',
            ],
        }
        
        detected_intent = "general"
        max_score = 0
        
        for intent_name, patterns in intents.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    score = len(pattern) / 50  # Simple scoring
                    if score > max_score:
                        max_score = score
                        detected_intent = intent_name
        
        # Extract entities
        # Email
        email_match = re.search(r'\b[\w.-]+@[\w.-]+\.\w+\b', message)
        if email_match:
            entities["email"] = email_match.group()
        
        # Phone
        phone_match = re.search(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', message)
        if phone_match:
            entities["phone"] = phone_match.group()
        
        # URL
        url_match = re.search(r'https?://\S+', message)
        if url_match:
            entities["url"] = url_match.group()
        
        # Question mark indicates FAQ
        if '?' in message and detected_intent == "general":
            detected_intent = "faq"
        
        return detected_intent, entities
    
    def _build_prompt(
        self,
        conversation_id: str,
        user_message: str,
        intent: str,
        entities: Dict[str, Any],
        knowledge_context: str,
        faq_answer: Optional[str],
    ) -> str:
        """Build the AI prompt.
        
        Args:
            conversation_id: Conversation ID
            user_message: User's message
            intent: Detected intent
            entities: Extracted entities
            knowledge_context: Retrieved knowledge
            faq_answer: FAQ answer if available
            
        Returns:
            Formatted prompt string
        """
        # Get business context
        bc = self.business_context_manager.get_context(self.business_id)
        
        # Build persona
        persona = f"""You are a professional customer success representative for {bc.business_name if bc else 'our business'}.
Your goal is to provide excellent customer service through natural, helpful conversations.

Tone: {bc.ai_tone if bc else 'friendly'} and {bc.ai_personality if bc else 'professional'}
Be helpful, knowledgeable, and empathetic. Always be honest if you don't have information.
Never make up information that isn't in your knowledge base.
"""
        
        # Build context
        context_parts = []
        
        if faq_answer:
            context_parts.append(f"FAQ Answer:\n{faq_answer}")
        elif knowledge_context:
            context_parts.append(f"Relevant Information:\n{knowledge_context}")
        
        if bc:
            if bc.description:
                context_parts.append(f"About Us: {bc.description}")
            if bc.website:
                context_parts.append(f"Website: {bc.website}")
        
        context = "\n\n".join(context_parts) if context_parts else "No specific context available."
        
        # Get conversation history
        recent_messages = self.conversation_memory.get_recent_messages(
            conversation_id=conversation_id,
            limit=5,
        )
        
        history_parts = []
        for msg in recent_messages:
            role = "Customer" if msg["role"] == "user" else "Assistant"
            history_parts.append(f"{role}: {msg['content']}")
        
        history = "\n".join(history_parts) if history_parts else "This is the start of the conversation."
        
        # Extract entities found
        entities_info = ""
        if entities:
            entities_info = f"\n\nExtracted Information:\n"
            for key, value in entities.items():
                entities_info += f"- {key}: {value}\n"
        
        prompt = f"""{persona}

CONTEXT:
{context}
{entities_info}

CONVERSATION HISTORY:
{history}

CURRENT MESSAGE:
Customer: {user_message}

Your response:"""
        
        return prompt
    
    async def _generate_response(
        self,
        prompt: str,
        request_id: str,
        max_retries: int = 3,
    ) -> Optional[str]:
        """Generate AI response with retry logic.
        
        Args:
            prompt: The formatted prompt
            request_id: Request identifier for logging
            max_retries: Maximum number of retries
            
        Returns:
            Generated response or None if failed
        """
        from services.ai_provider.base import Message, MessageRole
        
        # Prepare messages
        messages = [
            Message(role=MessageRole.USER, content=prompt),
        ]
        
        # Retry logic
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Log request
                self.logging_service.log_ai_request(
                    conversation_id="unknown",
                    business_id=self.business_id,
                    prompt=prompt,
                    model=self.config.get("model", "default"),
                    provider=self.config.get("provider", "auto"),
                )
                
                start_time = datetime.utcnow()
                
                # Call AI provider
                response = await self.ai_provider_manager.chat(
                    messages=messages,
                    temperature=self.config.get("temperature", 0.7),
                    max_tokens=self.config.get("max_tokens", 500),
                )
                
                duration = self._calc_time_ms(start_time)
                
                # Log response
                self.logging_service.log_ai_response(
                    conversation_id="unknown",
                    business_id=self.business_id,
                    response=response.content,
                    provider=response.provider.value if hasattr(response.provider, 'value') else str(response.provider),
                    duration_ms=duration,
                    tokens_used=response.usage.total_tokens if response.usage else None,
                )
                
                return response.content
                
            except Exception as e:
                last_error = e
                
                # Log error
                self.logging_service.log_error(
                    conversation_id="unknown",
                    business_id=self.business_id,
                    error=str(e),
                    context={"attempt": attempt + 1, "max_retries": max_retries},
                )
                
                # Exponential backoff
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
        
        # All retries failed
        return None
    
    def _should_request_human_takeover(
        self,
        conversation_id: str,
        intent: str,
        confidence: float,
    ) -> bool:
        """Determine if human takeover should be requested.
        
        Args:
            conversation_id: Conversation ID
            intent: Detected intent
            confidence: Response confidence score
            
        Returns:
            True if human takeover is needed
        """
        # High confidence intent with low response confidence
        if confidence < 0.5 and intent in ["pricing_inquiry", "purchase_intent"]:
            return True
        
        # Complaint or negative sentiment
        if intent == "complaint":
            return True
        
        # Explicit human request
        if intent == "human_request":
            return True
        
        # Very low confidence
        if confidence < 0.3:
            return True
        
        # Check conversation memory
        if self.conversation_memory.requires_human_intervention(conversation_id):
            return True
        
        return False
    
    def _generate_follow_ups(
        self,
        intent: str,
        entities: Dict[str, Any],
    ) -> List[str]:
        """Generate follow-up suggestions.
        
        Args:
            intent: Detected intent
            entities: Extracted entities
            
        Returns:
            List of follow-up suggestions
        """
        suggestions = {
            "greeting": [
                "How can I help you today?",
                "What brings you to our page?",
            ],
            "pricing_inquiry": [
                "Would you like more details on any specific product?",
                "Can I help you find something within your budget?",
            ],
            "purchase_intent": [
                "Would you like to place an order?",
                "Can I answer any questions before you purchase?",
            ],
            "product_inquiry": [
                "Is there a specific type of product you're looking for?",
                "Would you like recommendations based on your needs?",
            ],
            "appointment_request": [
                "What time works best for you?",
                "Would you prefer in-person or virtual?",
            ],
            "faq": [
                "Is there anything else you'd like to know?",
                "Can I help with anything else?",
            ],
        }
        
        return suggestions.get(intent, ["Is there anything else I can help you with?"])
    
    def _recommend_resources(
        self,
        intent: str,
        entities: Dict[str, Any],
    ) -> List[Dict[str, str]]:
        """Recommend resources based on intent.
        
        Args:
            intent: Detected intent
            entities: Extracted entities
            
        Returns:
            List of recommended resources
        """
        resources = []
        
        bc = self.business_context_manager.get_context(self.business_id)
        
        if intent in ["pricing_inquiry", "purchase_intent"]:
            if bc and bc.website:
                resources.append({
                    "type": "link",
                    "title": "Browse our products",
                    "url": bc.website,
                })
        
        if intent == "product_inquiry":
            resources.append({
                "type": "info",
                "title": "Our Products",
                "description": "Check out our full product catalog for more details.",
            })
        
        if intent == "service_inquiry":
            resources.append({
                "type": "info",
                "title": "Our Services",
                "description": "Learn more about how we can help you.",
            })
        
        if intent == "appointment_request":
            resources.append({
                "type": "cta",
                "title": "Book an Appointment",
                "description": "Schedule a time to speak with our team.",
            })
        
        return resources
    
    def _calc_time_ms(self, start: datetime) -> float:
        """Calculate time elapsed in milliseconds.
        
        Args:
            start: Start datetime
            
        Returns:
            Milliseconds elapsed
        """
        return (datetime.utcnow() - start).total_seconds() * 1000
    
    def get_conversation_summary(self, conversation_id: str) -> str:
        """Get summary of a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Conversation summary
        """
        return self.conversation_memory.get_conversation_summary(conversation_id)
    
    def get_lead_info(self, conversation_id: str) -> Dict[str, Any]:
        """Get lead information for a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Lead information dictionary
        """
        return self.conversation_memory.get_lead_status(conversation_id)
    
    def clear_conversation(self, conversation_id: str) -> bool:
        """Clear conversation from memory.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            True if cleared
        """
        return self.conversation_memory.clear_conversation(conversation_id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get overall statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            "status": self.status.value,
            "conversation_memory": self.conversation_memory.get_statistics(),
            "knowledge_base": self.knowledge_base.get_statistics(self.business_id),
            "logging": self.logging_service.get_statistics(),
            "moderation": self.moderation_layer.get_statistics(),
            "hallucination_prevention": self.hallucination_prevention.get_statistics(),
        }
