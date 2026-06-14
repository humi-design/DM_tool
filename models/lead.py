"""Lead model for managing potential customers from Instagram interactions."""

from app import db
from models.base import BaseModel, SoftDeleteMixin


class Lead(BaseModel, SoftDeleteMixin):
    """Lead model for managing potential customers from Instagram interactions."""
    
    __tablename__ = "leads"
    
    business_id = db.Column(
        db.String(36),
        db.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    source_type = db.Column(db.String(50), nullable=False, index=True)
    source_id = db.Column(db.String(100), nullable=True, index=True)
    
    instagram_user_id = db.Column(db.String(100), nullable=True, index=True)
    instagram_username = db.Column(db.String(255), nullable=True, index=True)
    instagram_profile_url = db.Column(db.String(500), nullable=True)
    
    name = db.Column(db.String(255), nullable=True, index=True)
    email = db.Column(db.String(255), nullable=True, index=True)
    phone = db.Column(db.String(20), nullable=True)
    
    status = db.Column(db.String(50), default="new", nullable=False, index=True)
    priority = db.Column(db.String(50), default="normal", nullable=False, index=True)
    
    assigned_to = db.Column(
        db.String(36),
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    tags = db.Column(db.JSON, default=list, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    score = db.Column(db.Integer, default=0, nullable=False, index=True)
    
    conversation_count = db.Column(db.Integer, default=0, nullable=False)
    last_conversation_at = db.Column(db.DateTime, nullable=True, index=True)
    
    funnel_stage = db.Column(db.String(50), nullable=True, index=True)
    converted_at = db.Column(db.DateTime, nullable=True, index=True)
    converted_to_id = db.Column(db.String(36), nullable=True)
    converted_to_type = db.Column(db.String(50), nullable=True)
    
    metadata_json = db.Column(db.JSON, default=dict, nullable=False)
    
    # Relationships
    business = db.relationship("Business", foreign_keys=[business_id], back_populates="leads")
    assignee = db.relationship("User", foreign_keys=[assigned_to])
    
    __table_args__ = (
        db.Index("idx_lead_business_status", "business_id", "status"),
        db.Index("idx_lead_assigned_status", "assigned_to", "status"),
        db.Index("idx_lead_instagram", "instagram_user_id", "business_id"),
        db.Index("idx_lead_priority_score", "priority", "score"),
        db.Index("idx_lead_conversion", "funnel_stage", "converted_at"),
    )
    
    STATUS_NEW = "new"
    STATUS_CONTACTED = "contacted"
    STATUS_QUALIFIED = "qualified"
    STATUS_PROPOSAL = "proposal"
    STATUS_NEGOTIATION = "negotiation"
    STATUS_WON = "won"
    STATUS_LOST = "lost"
    
    PRIORITY_LOW = "low"
    PRIORITY_NORMAL = "normal"
    PRIORITY_HIGH = "high"
    PRIORITY_URGENT = "urgent"
    
    def to_dict(self):
        """Convert lead to dictionary."""
        data = super().to_dict()
        data.pop("is_deleted", None)
        data.pop("deleted_at", None)
        return data
    
    def mark_converted(self, converted_to_id: str, converted_to_type: str) -> None:
        """Mark lead as converted."""
        self.converted_at = db.func.now()
        self.converted_to_id = converted_to_id
        self.converted_to_type = converted_to_type
        self.status = self.STATUS_WON
        db.session.commit()