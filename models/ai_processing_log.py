"""AI Processing Log Model - Stores comment intelligence processing history."""

from app import db
from models.base import BaseModel, SoftDeleteMixin


class AIProcessingLog(BaseModel, SoftDeleteMixin):
    """Model for storing AI processing logs from Comment Intelligence Engine."""
    
    __tablename__ = "ai_processing_logs"
    
    # Request identification
    request_id = db.Column(db.String(36), unique=True, nullable=False, index=True)
    
    # Comment data
    comment_text = db.Column(db.Text, nullable=False)
    author_username = db.Column(db.String(255), nullable=True, index=True)
    
    # Intent detection results
    intent = db.Column(db.String(50), nullable=False, index=True)
    intent_confidence = db.Column(db.Float, nullable=False)
    intent_reasoning = db.Column(db.Text, nullable=True)
    
    # Response data
    response_content = db.Column(db.Text, nullable=True)
    follow_up_suggestion = db.Column(db.Text, nullable=True)
    ai_result = db.Column(db.Text, nullable=True)
    
    # Decision data
    primary_action = db.Column(db.String(50), nullable=True)
    should_auto_reply = db.Column(db.Boolean, default=False, nullable=False)
    
    # Processing metadata
    processing_time_ms = db.Column(db.Float, nullable=True)
    ai_provider = db.Column(db.String(50), nullable=True)
    
    # Context data (stored as JSON)
    context_json = db.Column(db.JSON, default=dict, nullable=False)
    decision_json = db.Column(db.JSON, default=dict, nullable=False)
    emoji_reactions_json = db.Column(db.JSON, default=list, nullable=False)
    
    # Status
    is_error = db.Column(db.Boolean, default=False, nullable=False, index=True)
    error_message = db.Column(db.Text, nullable=True)
    
    # Business association
    business_id = db.Column(
        db.String(36),
        db.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    instagram_account_id = db.Column(
        db.String(36),
        db.ForeignKey("instagram_accounts.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    # Relationships
    business = db.relationship("Business", back_populates="ai_processing_logs")
    instagram_account = db.relationship("InstagramAccount", back_populates="ai_processing_logs")
    
    __table_args__ = (
        db.Index("idx_processing_log_intent_time", "intent", "created_at"),
        db.Index("idx_processing_log_author_time", "author_username", "created_at"),
        db.Index("idx_processing_log_business_time", "business_id", "created_at"),
    )
    
    def to_dict(self):
        """Convert to dictionary."""
        data = super().to_dict()
        data.pop("is_deleted", None)
        data.pop("deleted_at", None)
        return data
    
    @classmethod
    def create_from_result(cls, result, business_id=None, instagram_account_id=None):
        """Create a log entry from ProcessingResult.
        
        Args:
            result: ProcessingResult from CommentIntelligenceEngine
            business_id: Optional business ID
            instagram_account_id: Optional Instagram account ID
            
        Returns:
            AIProcessingLog instance
        """
        return cls(
            request_id=result.request_id,
            comment_text=result.comment_text,
            author_username=result.author_username,
            intent=result.intent.value if result.intent else "other",
            intent_confidence=result.intent_confidence,
            intent_reasoning=result.intent_reasoning,
            response_content=result.response_content,
            follow_up_suggestion=result.follow_up_suggestion,
            ai_result=result.ai_result,
            primary_action=result.decision.get("primary_action") if result.decision else None,
            should_auto_reply=result.should_auto_reply,
            processing_time_ms=result.processing_time_ms,
            context_json=result.context or {},
            decision_json=result.decision or {},
            emoji_reactions_json=result.emoji_reactions,
            is_error=bool(result.error),
            error_message=result.error,
            business_id=business_id,
            instagram_account_id=instagram_account_id,
        )