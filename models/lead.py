"""Lead model for managing potential customers from Instagram interactions."""

from datetime import datetime
from app import db
from models.base import BaseModel, SoftDeleteMixin


class Lead(BaseModel, SoftDeleteMixin):
    """Lead model for managing potential customers from Instagram interactions."""
    
    __tablename__ = "leads"
    
    # Basic Information
    name = db.Column(db.String(255), nullable=True, index=True)
    email = db.Column(db.String(255), nullable=True, index=True)
    phone = db.Column(db.String(50), nullable=True)
    company = db.Column(db.String(255), nullable=True, index=True)
    
    # Budget & Interest
    budget = db.Column(db.String(100), nullable=True)  # e.g., "$5,000 - $10,000"
    interest = db.Column(db.Text, nullable=True)
    requirements = db.Column(db.Text, nullable=True)
    
    # Source Information
    source_type = db.Column(db.String(50), nullable=False, index=True)
    source_id = db.Column(db.String(100), nullable=True, index=True)
    source_name = db.Column(db.String(255), nullable=True)  # e.g., "Instagram Post", "DM Campaign"
    
    # Instagram specific
    instagram_user_id = db.Column(db.String(100), nullable=True, index=True)
    instagram_username = db.Column(db.String(255), nullable=True, index=True)
    instagram_profile_url = db.Column(db.String(500), nullable=True)
    
    # Business relation
    business_id = db.Column(
        db.String(36),
        db.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Lead Status & Temperature
    lead_status = db.Column(db.String(20), default="cold", nullable=False, index=True)  # hot, warm, cold
    status = db.Column(db.String(50), default="new", nullable=False, index=True)  # Pipeline status
    priority = db.Column(db.String(50), default="normal", nullable=False, index=True)
    
    # AI Scoring (0-100)
    lead_score = db.Column(db.Integer, default=0, nullable=False, index=True)
    ai_confidence = db.Column(db.Float, nullable=True)  # AI confidence in score (0-1)
    
    # Assignment
    assigned_to = db.Column(
        db.String(36),
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Tags and Notes
    tags = db.Column(db.JSON, default=list, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    ai_generated_notes = db.Column(db.Text, nullable=True)  # AI-generated insights
    ai_summary = db.Column(db.Text, nullable=True)  # AI conversation summary
    
    # Conversation tracking
    conversation_count = db.Column(db.Integer, default=0, nullable=False)
    last_conversation_at = db.Column(db.DateTime, nullable=True, index=True)
    
    # Pipeline & Conversion
    funnel_stage = db.Column(db.String(50), nullable=True, index=True)
    converted_at = db.Column(db.DateTime, nullable=True, index=True)
    converted_to_id = db.Column(db.String(36), nullable=True)
    converted_to_type = db.Column(db.String(50), nullable=True)
    
    # Timeline
    last_contacted_at = db.Column(db.DateTime, nullable=True)
    next_follow_up = db.Column(db.DateTime, nullable=True)
    
    # Metadata
    metadata_json = db.Column(db.JSON, default=dict, nullable=False)
    
    # Relationships
    business = db.relationship("Business", foreign_keys=[business_id], back_populates="leads")
    assignee = db.relationship("User", foreign_keys=[assigned_to])
    timeline_events = db.relationship("LeadTimelineEvent", back_populates="lead", lazy="dynamic", cascade="all, delete-orphan")
    
    __table_args__ = (
        db.Index("idx_lead_business_status", "business_id", "status"),
        db.Index("idx_lead_business_lead_status", "business_id", "lead_status"),
        db.Index("idx_lead_assigned_status", "assigned_to", "status"),
        db.Index("idx_lead_instagram", "instagram_user_id", "business_id"),
        db.Index("idx_lead_priority_score", "priority", "lead_score"),
        db.Index("idx_lead_conversion", "funnel_stage", "converted_at"),
        db.Index("idx_lead_company", "company"),
        db.Index("idx_lead_email", "email"),
    )
    
    # Lead Temperature Status
    STATUS_HOT = "hot"
    STATUS_WARM = "warm"
    STATUS_COLD = "cold"
    
    # Pipeline Status
    PIPELINE_NEW = "new"
    PIPELINE_CONTACTED = "contacted"
    PIPELINE_QUALIFIED = "qualified"
    PIPELINE_PROPOSAL = "proposal"
    PIPELINE_WON = "won"
    PIPELINE_LOST = "lost"
    
    # Priority
    PRIORITY_LOW = "low"
    PRIORITY_NORMAL = "normal"
    PRIORITY_HIGH = "high"
    PRIORITY_URGENT = "urgent"
    
    @property
    def temperature_color(self):
        """Return color based on lead temperature."""
        colors = {
            self.STATUS_HOT: "#ef4444",  # Red
            self.STATUS_WARM: "#f59e0b",  # Amber
            self.STATUS_COLD: "#3b82f6",  # Blue
        }
        return colors.get(self.lead_status, "#6b7280")
    
    @property
    def temperature_icon(self):
        """Return icon based on lead temperature."""
        icons = {
            self.STATUS_HOT: "🔥",
            self.STATUS_WARM: "🌡️",
            self.STATUS_COLD: "❄️",
        }
        return icons.get(self.lead_status, "📊")
    
    @property
    def score_label(self):
        """Return human-readable score label."""
        if self.lead_score >= 80:
            return "Excellent"
        elif self.lead_score >= 60:
            return "Good"
        elif self.lead_score >= 40:
            return "Average"
        elif self.lead_score >= 20:
            return "Low"
        return "Very Low"
    
    def to_dict(self):
        """Convert lead to dictionary."""
        data = super().to_dict()
        data.pop("is_deleted", None)
        data.pop("deleted_at", None)
        data["temperature_color"] = self.temperature_color
        data["temperature_icon"] = self.temperature_icon
        data["score_label"] = self.score_label
        return data
    
    def add_timeline_event(self, event_type: str, description: str, metadata: dict = None) -> "LeadTimelineEvent":
        """Add a timeline event to the lead."""
        event = LeadTimelineEvent(
            lead_id=self.id,
            event_type=event_type,
            description=description,
            metadata_json=metadata or {}
        )
        db.session.add(event)
        db.session.commit()
        return event
    
    def mark_converted(self, converted_to_id: str, converted_to_type: str) -> None:
        """Mark lead as converted."""
        self.converted_at = datetime.utcnow()
        self.converted_to_id = converted_to_id
        self.converted_to_type = converted_to_type
        self.status = self.PIPELINE_WON
        self.add_timeline_event("converted", f"Lead converted to {converted_to_type}")
        db.session.commit()


class LeadTimelineEvent(BaseModel):
    """Timeline events for lead tracking."""
    
    __tablename__ = "lead_timeline_events"
    
    lead_id = db.Column(
        db.String(36),
        db.ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    event_type = db.Column(db.String(50), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    metadata_json = db.Column(db.JSON, default=dict, nullable=False)
    
    # Relationships
    lead = db.relationship("Lead", foreign_keys=[lead_id], back_populates="timeline_events")
    
    # Event types
    EVENT_CREATED = "created"
    EVENT_UPDATED = "updated"
    EVENT_STATUS_CHANGED = "status_changed"
    EVENT_SCORE_CHANGED = "score_changed"
    EVENT_ASSIGNED = "assigned"
    EVENT_NOTE_ADDED = "note_added"
    EVENT_EMAIL_SENT = "email_sent"
    EVENT_CALL_MADE = "call_made"
    EVENT_MEETING_SCHEDULED = "meeting_scheduled"
    EVENT_CONVERSATION = "conversation"
    EVENT_AI_SUMMARY = "ai_summary"
    EVENT_CONVERTED = "converted"
    
    def to_dict(self):
        """Convert event to dictionary."""
        data = super().to_dict()
        return data