"""Context Builder Module - Builds rich context for comment processing.

This module creates comprehensive context from comments, user history,
business information, and conversation threads for accurate AI processing.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from models.comment import Comment
    from models.user import User
    from models.business import Business


@dataclass
class CommentContext:
    """Rich context for comment processing."""
    # Original comment data
    comment_id: Optional[str] = None
    comment_text: str = ""
    author_username: Optional[str] = None
    author_name: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    # User context
    user_id: Optional[str] = None
    user_previous_comments: List[str] = field(default_factory=list)
    user_interaction_count: int = 0
    user_first_seen: Optional[datetime] = None
    
    # Business context
    business_id: Optional[str] = None
    business_name: Optional[str] = None
    business_description: Optional[str] = None
    business_category: Optional[str] = None
    
    # Conversation context
    is_reply: bool = False
    parent_comment: Optional[str] = None
    reply_count: int = 0
    conversation_thread: List[str] = field(default_factory=list)
    
    # Engagement context
    like_count: int = 0
    has_attachments: bool = False
    has_emoji: bool = False
    
    # Intent context (populated after intent detection)
    detected_intent: Optional[str] = None
    intent_confidence: float = 0.0
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    processing_timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for AI processing."""
        return {
            "comment": {
                "text": self.comment_text,
                "author": {
                    "username": self.author_username,
                    "name": self.author_name,
                },
                "timestamp": self.timestamp.isoformat() if self.timestamp else None,
                "is_reply": self.is_reply,
                "like_count": self.like_count,
                "has_emoji": self.has_emoji,
            },
            "user": {
                "id": self.user_id,
                "previous_interactions": self.user_interaction_count,
                "previous_comments": self.user_previous_comments[-5:],  # Last 5 comments
                "first_seen": self.user_first_seen.isoformat() if self.user_first_seen else None,
            },
            "business": {
                "id": self.business_id,
                "name": self.business_name,
                "description": self.business_description,
                "category": self.business_category,
            },
            "conversation": {
                "is_thread": self.is_reply,
                "parent_comment": self.parent_comment,
                "reply_count": self.reply_count,
                "thread": self.conversation_thread[-3:],  # Last 3 messages in thread
            },
            "intent": {
                "detected": self.detected_intent,
                "confidence": self.intent_confidence,
            },
            "metadata": self.metadata,
        }
    
    def to_prompt_context(self) -> str:
        """Convert context to a formatted string for AI prompts."""
        sections = []
        
        sections.append("## Comment Context")
        sections.append(f"Comment: \"{self.comment_text}\"")
        if self.author_username:
            sections.append(f"Author: @{self.author_username}")
        
        if self.business_name:
            sections.append(f"\n## Business")
            sections.append(f"Business: {self.business_name}")
            if self.business_description:
                sections.append(f"Description: {self.business_description}")
            if self.business_category:
                sections.append(f"Category: {self.business_category}")
        
        if self.user_interaction_count > 0:
            sections.append(f"\n## User History")
            sections.append(f"Previous interactions: {self.user_interaction_count}")
            if self.user_previous_comments:
                sections.append("Previous comments:")
                for prev in self.user_previous_comments[-3:]:
                    sections.append(f"  - \"{prev}\"")
        
        if self.is_reply:
            sections.append(f"\n## Conversation")
            sections.append(f"Replying to: \"{self.parent_comment}\"")
            sections.append(f"Thread replies: {self.reply_count}")
        
        if self.detected_intent:
            sections.append(f"\n## Detected Intent")
            sections.append(f"Intent: {self.detected_intent} (confidence: {self.intent_confidence:.2f})")
        
        return "\n".join(sections)


class ContextBuilder:
    """Builds rich context for comment processing.
    
    This class aggregates information from various sources to create
    a comprehensive context for accurate AI-powered comment processing.
    """
    
    def __init__(self, db=None):
        """Initialize the context builder.
        
        Args:
            db: Optional database instance for fetching related data
        """
        self._db = db
    
    async def build(
        self,
        comment_text: str,
        comment: Optional["Comment"] = None,
        user: Optional["User"] = None,
        business: Optional["Business"] = None,
        **kwargs
    ) -> CommentContext:
        """Build comprehensive context for a comment.
        
        Args:
            comment_text: The comment text
            comment: Optional Comment model instance
            user: Optional User model instance
            business: Optional Business model instance
            **kwargs: Additional context data
            
        Returns:
            CommentContext with all relevant information
        """
        context = CommentContext(
            comment_text=comment_text,
            **kwargs
        )
        
        # Populate from Comment model
        if comment:
            context.comment_id = str(comment.id) if comment.id else None
            context.author_username = comment.author_username
            context.author_name = comment.author_name
            context.timestamp = comment.timestamp
            context.is_reply = comment.is_reply
            context.like_count = comment.like_count
            context.reply_count = comment.reply_count
            context.metadata = comment.metadata_json or {}
            
            # Check for emoji in comment
            context.has_emoji = self._contains_emoji(comment_text)
            
            # Check for attachments
            context.has_attachments = bool(context.metadata.get("attachments"))
            
            # Get parent comment if reply
            if comment.is_reply and comment.parent:
                context.parent_comment = comment.parent.text
        
        # Populate from User model
        if user:
            context.user_id = str(user.id) if user.id else None
            context.user_first_seen = getattr(user, 'created_at', None)
            
            # Get user interaction count (would need DB query in real implementation)
            if self._db:
                context.user_interaction_count = await self._get_user_interaction_count(user.id)
                context.user_previous_comments = await self._get_user_previous_comments(user.id)
        
        # Populate from Business model
        if business:
            context.business_id = str(business.id) if business.id else None
            context.business_name = business.name
            context.business_description = getattr(business, 'description', None)
            context.business_category = getattr(business, 'category', None)
        
        return context
    
    def _contains_emoji(self, text: str) -> bool:
        """Check if text contains emoji characters."""
        import re
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"  # dingbats
            "\U000024C2-\U0001F251"
            "]+", 
            flags=re.UNICODE
        )
        return bool(emoji_pattern.search(text))
    
    async def _get_user_interaction_count(self, user_id: str) -> int:
        """Get total comment interaction count for a user."""
        if not self._db:
            return 0
        
        try:
            from models.comment import Comment
            from app import db
            
            count = db.session.query(Comment).filter(
                Comment.user_id == user_id,
                Comment.is_deleted == False
            ).count()
            return count
        except Exception:
            return 0
    
    async def _get_user_previous_comments(self, user_id: str, limit: int = 10) -> List[str]:
        """Get user's previous comments."""
        if not self._db:
            return []
        
        try:
            from models.comment import Comment
            from app import db
            
            comments = db.session.query(Comment).filter(
                Comment.user_id == user_id,
                Comment.is_deleted == False
            ).order_by(Comment.timestamp.desc()).limit(limit).all()
            
            return [c.text for c in comments]
        except Exception:
            return []
    
    def enrich_with_intent(self, context: CommentContext, intent: str, confidence: float) -> CommentContext:
        """Enrich context with intent detection results.
        
        Args:
            context: The context to enrich
            intent: Detected intent
            confidence: Intent detection confidence
            
        Returns:
            Enriched context
        """
        context.detected_intent = intent
        context.intent_confidence = confidence
        return context