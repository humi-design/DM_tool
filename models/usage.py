"""Usage tracking model for billing."""

from datetime import datetime, timedelta

from app import db
from models.base import BaseModel


class UsageRecord(BaseModel):
    """Usage tracking model for API calls, AI requests, storage, etc."""
    
    __tablename__ = "usage_records"
    
    organization_id = db.Column(
        db.String(36),
        db.ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    subscription_id = db.Column(
        db.String(36),
        db.ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Usage type
    usage_type = db.Column(db.String(50), nullable=False, index=True)
    
    # Time period
    period_start = db.Column(db.DateTime, nullable=False, index=True)
    period_end = db.Column(db.DateTime, nullable=False, index=True)
    period_type = db.Column(db.String(20), default="monthly", nullable=False)  # daily, monthly, yearly
    
    # Count and limits
    count = db.Column(db.Integer, default=0, nullable=False)
    included = db.Column(db.Integer, default=0, nullable=False)  # Included in plan
    overage = db.Column(db.Integer, default=0, nullable=False)  # Usage beyond included
    
    # Cost
    unit_cost = db.Column(db.Numeric(10, 4), default=0, nullable=False)
    overage_cost = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    
    # Metadata
    metadata_json = db.Column(db.JSON, default=dict, nullable=False)
    
    # Relationships
    organization = db.relationship("Organization", back_populates="usage_records")
    subscription = db.relationship("Subscription", back_populates="usage_records")
    
    __table_args__ = (
        db.Index("idx_usage_org_type_period", "organization_id", "usage_type", "period_start"),
        db.Index("idx_usage_period", "period_start", "period_end"),
    )
    
    # Usage type constants
    TYPE_API_REQUESTS = "api_requests"
    TYPE_AI_REQUESTS = "ai_requests"
    TYPE_STORAGE_MB = "storage_mb"
    TYPE_MESSAGES_SENT = "messages_sent"
    TYPE_LEADS_CAPTURED = "leads_captured"
    TYPE_COMMENTS_PROCESSED = "comments_processed"
    TYPE_DM_SENT = "dm_sent"
    TYPE_REPORTS_GENERATED = "reports_generated"
    
    # Period type constants
    PERIOD_DAILY = "daily"
    PERIOD_MONTHLY = "monthly"
    PERIOD_YEARLY = "yearly"
    
    def to_dict(self):
        """Convert usage record to dictionary."""
        return super().to_dict()
    
    @property
    def total_cost(self):
        """Calculate total cost."""
        return float(self.overage_cost)
    
    @property
    def is_over_included(self) -> bool:
        """Check if usage exceeds included amount."""
        return self.count > self.included if self.included else False
    
    @property
    def included_remaining(self) -> int:
        """Get remaining included usage."""
        if not self.included:
            return float('inf') if self.count < float('inf') else 0
        return max(0, self.included - self.count)
    
    def add_usage(self, count: int, metadata: dict = None) -> None:
        """Add usage count."""
        self.count += count
        if metadata:
            self.metadata_json.update(metadata)
        self._calculate_overage()
        db.session.commit()
    
    def _calculate_overage(self) -> None:
        """Calculate overage based on included amount."""
        if self.included and self.count > self.included:
            self.overage = self.count - self.included
            self.overage_cost = self.overage * float(self.unit_cost)
        else:
            self.overage = 0
            self.overage_cost = 0
    
    @classmethod
    def get_or_create_current(
        cls,
        organization_id: str,
        usage_type: str,
        subscription_id: str = None
    ) -> "UsageRecord":
        """Get or create current period usage record."""
        now = datetime.utcnow()
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        period_end = (period_start + timedelta(days=32)).replace(day=1)
        
        record = cls.query.filter(
            cls.organization_id == organization_id,
            cls.usage_type == usage_type,
            cls.period_start == period_start
        ).first()
        
        if not record:
            record = cls(
                organization_id=organization_id,
                subscription_id=subscription_id,
                usage_type=usage_type,
                period_start=period_start,
                period_end=period_end,
                period_type=cls.PERIOD_MONTHLY
            )
            db.session.add(record)
            db.session.commit()
        
        return record
    
    @classmethod
    def get_usage_summary(cls, organization_id: str, period_start: datetime = None, period_end: datetime = None):
        """Get usage summary for organization."""
        query = cls.query.filter(cls.organization_id == organization_id)
        
        if period_start:
            query = query.filter(cls.period_start >= period_start)
        if period_end:
            query = query.filter(cls.period_end <= period_end)
        
        return query.all()
    
    @classmethod
    def get_total_by_type(cls, organization_id: str, usage_type: str, days: int = 30) -> int:
        """Get total usage for type in last N days."""
        start_date = datetime.utcnow() - timedelta(days=days)
        records = cls.query.filter(
            cls.organization_id == organization_id,
            cls.usage_type == usage_type,
            cls.period_start >= start_date
        ).all()
        
        return sum(r.count for r in records)


class OrganizationUsage(BaseModel):
    """Aggregated usage tracking per organization per period."""
    
    __tablename__ = "organization_usage"
    
    organization_id = db.Column(
        db.String(36),
        db.ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Period
    period_start = db.Column(db.DateTime, nullable=False, index=True)
    period_end = db.Column(db.DateTime, nullable=False, index=True)
    period_type = db.Column(db.String(20), default="monthly", nullable=False)
    
    # Aggregated counts
    api_requests = db.Column(db.Integer, default=0, nullable=False)
    ai_requests = db.Column(db.Integer, default=0, nullable=False)
    storage_mb = db.Column(db.Integer, default=0, nullable=False)
    messages_sent = db.Column(db.Integer, default=0, nullable=False)
    leads_captured = db.Column(db.Integer, default=0, nullable=False)
    comments_processed = db.Column(db.Integer, default=0, nullable=False)
    dm_sent = db.Column(db.Integer, default=0, nullable=False)
    
    # Custom tracked metrics
    custom_metrics = db.Column(db.JSON, default=dict, nullable=False)
    
    # Last updated
    last_activity_at = db.Column(db.DateTime, nullable=True)
    
    # Metadata
    metadata_json = db.Column(db.JSON, default=dict, nullable=False)
    
    # Relationships
    organization = db.relationship("Organization", back_populates="organization_usage")
    
    __table_args__ = (
        db.Index("idx_org_usage_period", "organization_id", "period_start"),
    )
    
    def to_dict(self):
        """Convert to dictionary."""
        data = super().to_dict()
        data["usage"] = {
            "api_requests": self.api_requests,
            "ai_requests": self.ai_requests,
            "storage_mb": self.storage_mb,
            "messages_sent": self.messages_sent,
            "leads_captured": self.leads_captured,
            "comments_processed": self.comments_processed,
            "dm_sent": self.dm_sent,
        }
        data["usage"].update(self.custom_metrics or {})
        return data
    
    @classmethod
    def get_or_create_current(cls, organization_id: str) -> "OrganizationUsage":
        """Get or create current period usage."""
        now = datetime.utcnow()
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        period_end = (period_start + timedelta(days=32)).replace(day=1)
        
        usage = cls.query.filter(
            cls.organization_id == organization_id,
            cls.period_start == period_start
        ).first()
        
        if not usage:
            usage = cls(
                organization_id=organization_id,
                period_start=period_start,
                period_end=period_end,
                period_type="monthly"
            )
            db.session.add(usage)
            db.session.commit()
        
        return usage
    
    def increment(self, metric: str, count: int = 1) -> None:
        """Increment a usage metric."""
        if hasattr(self, metric):
            current = getattr(self, metric) or 0
            setattr(self, metric, current + count)
        elif self.custom_metrics is None:
            self.custom_metrics = {}
            self.custom_metrics[metric] = count
        else:
            self.custom_metrics[metric] = self.custom_metrics.get(metric, 0) + count
        
        self.last_activity_at = datetime.utcnow()
        db.session.commit()
    
    def get_usage_breakdown(self) -> dict:
        """Get usage breakdown for API response."""
        return {
            "api_requests": {"count": self.api_requests},
            "ai_requests": {"count": self.ai_requests},
            "storage_mb": {"count": self.storage_mb},
            "messages_sent": {"count": self.messages_sent},
            "leads_captured": {"count": self.leads_captured},
            "comments_processed": {"count": self.comments_processed},
            "dm_sent": {"count": self.dm_sent},
        }