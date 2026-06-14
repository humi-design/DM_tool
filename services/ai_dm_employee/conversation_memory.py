"""Conversation Memory Manager - Manages conversation history and customer context."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from collections import defaultdict
import json


@dataclass
class ConversationContext:
    """Stores all context for a conversation."""
    conversation_id: str
    participant_id: str
    participant_username: str
    
    # Conversation history
    messages: List[Dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    
    # Customer interests and preferences
    interests: List[str] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)
    
    # FAQ history - tracks what questions have been asked
    faq_asked: List[str] = field(default_factory=list)
    faq_satisfaction: Dict[str, int] = field(default_factory=dict)
    
    # Lead status tracking
    lead_status: str = "new"
    lead_score: int = 0
    lead_qualification: Dict[str, Any] = field(default_factory=dict)
    
    # Resources shared during conversation
    resources_shared: List[str] = field(default_factory=list)
    
    # Business context loaded
    business_context_loaded: bool = False
    business_context: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    interaction_count: int = 0
    
    # Human takeover flag
    requires_human: bool = False
    human_takeover_reason: Optional[str] = None


class ConversationMemoryManager:
    """Manages conversation memory and customer context across interactions.
    
    Responsibilities:
    - Store and retrieve conversation history
    - Track customer interests and preferences
    - Maintain FAQ history
    - Track lead status and qualification
    - Manage resources shared
    - Handle human takeover requests
    """
    
    def __init__(self, max_history_per_conversation: int = 50):
        """Initialize the conversation memory manager.
        
        Args:
            max_history_per_conversation: Maximum messages to store per conversation
        """
        self._memory: Dict[str, ConversationContext] = {}
        self.max_history_per_conversation = max_history_per_conversation
        
        # In-memory cache for fast access
        self._cache: Dict[str, datetime] = {}
        self._cache_expiry_seconds = 3600  # 1 hour
    
    def get_or_create_context(
        self,
        conversation_id: str,
        participant_id: str,
        participant_username: str,
    ) -> ConversationContext:
        """Get existing context or create new one for a conversation.
        
        Args:
            conversation_id: Unique conversation identifier
            participant_id: Instagram user ID
            participant_username: Instagram username
            
        Returns:
            ConversationContext for the conversation
        """
        if conversation_id not in self._memory:
            self._memory[conversation_id] = ConversationContext(
                conversation_id=conversation_id,
                participant_id=participant_id,
                participant_username=participant_username,
            )
        
        context = self._memory[conversation_id]
        context.last_updated = datetime.utcnow()
        return context
    
    def get_context(self, conversation_id: str) -> Optional[ConversationContext]:
        """Retrieve conversation context.
        
        Args:
            conversation_id: Conversation to retrieve
            
        Returns:
            ConversationContext or None if not found
        """
        return self._memory.get(conversation_id)
    
    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Add a message to conversation history.
        
        Args:
            conversation_id: Conversation to add message to
            role: Message sender role (user/assistant/system)
            content: Message content
            metadata: Optional message metadata
            
        Returns:
            True if added successfully
        """
        context = self.get_context(conversation_id)
        if not context:
            return False
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }
        
        context.messages.append(message)
        context.interaction_count += 1
        
        # Trim history if needed
        if len(context.messages) > self.max_history_per_conversation:
            context.messages = context.messages[-self.max_history_per_conversation:]
        
        context.last_updated = datetime.utcnow()
        return True
    
    def get_recent_messages(
        self,
        conversation_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get recent messages from conversation.
        
        Args:
            conversation_id: Conversation to retrieve from
            limit: Number of recent messages to retrieve
            
        Returns:
            List of recent messages
        """
        context = self.get_context(conversation_id)
        if not context:
            return []
        
        return context.messages[-limit:] if context.messages else []
    
    def get_conversation_summary(self, conversation_id: str) -> str:
        """Get a summary of the conversation.
        
        Args:
            conversation_id: Conversation to summarize
            
        Returns:
            Summary string
        """
        context = self.get_context(conversation_id)
        if not context:
            return ""
        
        if context.summary:
            return context.summary
        
        # Generate a quick summary from recent messages
        messages = context.messages[-10:] if context.messages else []
        if not messages:
            return "New conversation started."
        
        user_messages = [m for m in messages if m.get("role") == "user"]
        assistant_messages = [m for m in messages if m.get("role") == "assistant"]
        
        summary_parts = [
            f"Participant: @{context.participant_username}",
            f"Total interactions: {context.interaction_count}",
            f"Lead status: {context.lead_status}",
            f"Resources shared: {len(context.resources_shared)}",
            f"User messages: {len(user_messages)}",
            f"Assistant responses: {len(assistant_messages)}",
        ]
        
        if context.interests:
            summary_parts.append(f"Interests: {', '.join(context.interests[:5])}")
        
        return " | ".join(summary_parts)
    
    def add_interest(self, conversation_id: str, interest: str) -> bool:
        """Add a customer interest.
        
        Args:
            conversation_id: Conversation to update
            interest: Interest to add
            
        Returns:
            True if added successfully
        """
        context = self.get_context(conversation_id)
        if not context:
            return False
        
        if interest not in context.interests:
            context.interests.append(interest)
            context.last_updated = datetime.utcnow()
        
        return True
    
    def get_interests(self, conversation_id: str) -> List[str]:
        """Get customer interests.
        
        Args:
            conversation_id: Conversation to retrieve from
            
        Returns:
            List of interests
        """
        context = self.get_context(conversation_id)
        return context.interests if context else []
    
    def add_faq_interaction(
        self,
        conversation_id: str,
        faq_question: str,
        satisfied: bool = True,
    ) -> bool:
        """Record a FAQ interaction.
        
        Args:
            conversation_id: Conversation to update
            faq_question: The FAQ question that was asked
            satisfied: Whether the user was satisfied with the answer
            
        Returns:
            True if recorded successfully
        """
        context = self.get_context(conversation_id)
        if not context:
            return False
        
        context.faq_asked.append(faq_question)
        context.faq_satisfaction[faq_question] = 1 if satisfied else 0
        context.last_updated = datetime.utcnow()
        return True
    
    def update_lead_status(
        self,
        conversation_id: str,
        status: str,
        score: Optional[int] = None,
        qualification: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update lead status and qualification.
        
        Args:
            conversation_id: Conversation to update
            status: New lead status
            score: Optional new lead score
            qualification: Optional qualification data
            
        Returns:
            True if updated successfully
        """
        context = self.get_context(conversation_id)
        if not context:
            return False
        
        context.lead_status = status
        if score is not None:
            context.lead_score = score
        if qualification:
            context.lead_qualification.update(qualification)
        
        context.last_updated = datetime.utcnow()
        return True
    
    def get_lead_status(self, conversation_id: str) -> Dict[str, Any]:
        """Get lead status information.
        
        Args:
            conversation_id: Conversation to retrieve from
            
        Returns:
            Dictionary with lead status information
        """
        context = self.get_context(conversation_id)
        if not context:
            return {"status": "unknown", "score": 0}
        
        return {
            "status": context.lead_status,
            "score": context.lead_score,
            "qualification": context.lead_qualification,
            "interaction_count": context.interaction_count,
        }
    
    def add_resource_shared(
        self,
        conversation_id: str,
        resource_id: str,
        resource_type: str,
    ) -> bool:
        """Record a resource that was shared.
        
        Args:
            conversation_id: Conversation to update
            resource_id: Resource identifier
            resource_type: Type of resource
            
        Returns:
            True if recorded successfully
        """
        context = self.get_context(conversation_id)
        if not context:
            return False
        
        resource_ref = f"{resource_type}:{resource_id}"
        if resource_ref not in context.resources_shared:
            context.resources_shared.append(resource_ref)
            context.last_updated = datetime.utcnow()
        
        return True
    
    def get_resources_shared(self, conversation_id: str) -> List[str]:
        """Get list of resources shared in conversation.
        
        Args:
            conversation_id: Conversation to retrieve from
            
        Returns:
            List of resource references
        """
        context = self.get_context(conversation_id)
        return context.resources_shared if context else []
    
    def set_business_context(
        self,
        conversation_id: str,
        business_context: Dict[str, Any],
    ) -> bool:
        """Set business context for a conversation.
        
        Args:
            conversation_id: Conversation to update
            business_context: Business context data
            
        Returns:
            True if set successfully
        """
        context = self.get_context(conversation_id)
        if not context:
            return False
        
        context.business_context = business_context
        context.business_context_loaded = True
        context.last_updated = datetime.utcnow()
        return True
    
    def get_business_context(self, conversation_id: str) -> Dict[str, Any]:
        """Get business context for a conversation.
        
        Args:
            conversation_id: Conversation to retrieve from
            
        Returns:
            Business context dictionary
        """
        context = self.get_context(conversation_id)
        return context.business_context if context else {}
    
    def request_human_takeover(
        self,
        conversation_id: str,
        reason: str,
    ) -> bool:
        """Request human takeover for a conversation.
        
        Args:
            conversation_id: Conversation to flag
            reason: Reason for human takeover
            
        Returns:
            True if flagged successfully
        """
        context = self.get_context(conversation_id)
        if not context:
            return False
        
        context.requires_human = True
        context.human_takeover_reason = reason
        context.last_updated = datetime.utcnow()
        return True
    
    def clear_human_takeover(self, conversation_id: str) -> bool:
        """Clear human takeover flag.
        
        Args:
            conversation_id: Conversation to update
            
        Returns:
            True if cleared successfully
        """
        context = self.get_context(conversation_id)
        if not context:
            return False
        
        context.requires_human = False
        context.human_takeover_reason = None
        context.last_updated = datetime.utcnow()
        return True
    
    def requires_human_intervention(self, conversation_id: str) -> bool:
        """Check if conversation requires human intervention.
        
        Args:
            conversation_id: Conversation to check
            
        Returns:
            True if human intervention is needed
        """
        context = self.get_context(conversation_id)
        return context.requires_human if context else False
    
    def build_context_prompt(
        self,
        conversation_id: str,
        include_history: bool = True,
        include_interests: bool = True,
        include_lead_info: bool = True,
    ) -> str:
        """Build a context prompt for the AI.
        
        Args:
            conversation_id: Conversation to build context for
            include_history: Include message history
            include_interests: Include customer interests
            include_lead_info: Include lead status
            
        Returns:
            Formatted context string
        """
        context = self.get_context(conversation_id)
        if not context:
            return ""
        
        parts = []
        
        # Participant info
        parts.append(f"Customer: @{context.participant_username}")
        parts.append(f"Conversation started: {context.created_at.isoformat()}")
        
        # Interests
        if include_interests and context.interests:
            parts.append(f"Known interests: {', '.join(context.interests)}")
        
        # Lead info
        if include_lead_info:
            parts.append(f"Lead status: {context.lead_status}")
            parts.append(f"Lead score: {context.lead_score}")
            if context.lead_qualification:
                parts.append(f"Qualification data: {json.dumps(context.lead_qualification)}")
        
        # Resources shared
        if context.resources_shared:
            parts.append(f"Resources already shared: {len(context.resources_shared)}")
        
        # Business context
        if context.business_context:
            parts.append(f"Business: {context.business_context.get('name', 'Unknown')}")
        
        # Recent conversation (if included)
        if include_history and context.messages:
            recent = context.messages[-5:]
            history_lines = []
            for msg in recent:
                role_label = "Customer" if msg["role"] == "user" else "Assistant"
                history_lines.append(f"{role_label}: {msg['content'][:200]}")
            if history_lines:
                parts.append("Recent conversation:\n" + "\n".join(history_lines))
        
        return "\n".join(parts)
    
    def clear_conversation(self, conversation_id: str) -> bool:
        """Clear a conversation from memory.
        
        Args:
            conversation_id: Conversation to clear
            
        Returns:
            True if cleared successfully
        """
        if conversation_id in self._memory:
            del self._memory[conversation_id]
            return True
        return False
    
    def get_all_conversations_needing_human(self) -> List[str]:
        """Get all conversation IDs that need human intervention.
        
        Returns:
            List of conversation IDs
        """
        return [
            conv_id for conv_id, ctx in self._memory.items()
            if ctx.requires_human
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get memory manager statistics.
        
        Returns:
            Statistics dictionary
        """
        total_conversations = len(self._memory)
        total_messages = sum(len(ctx.messages) for ctx in self._memory.values())
        human_takeover_count = sum(
            1 for ctx in self._memory.values() if ctx.requires_human
        )
        
        return {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "human_takeover_pending": human_takeover_count,
            "memory_usage_mb": self._estimate_memory_usage(),
        }
    
    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in MB.
        
        Returns:
            Estimated memory usage
        """
        import sys
        return sys.getsizeof(json.dumps(self._memory)) / (1024 * 1024)
