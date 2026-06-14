"""Report model for analytics and business reports."""

from app import db
from models.base import BaseModel, SoftDeleteMixin


class Report(BaseModel, SoftDeleteMixin):
    """Report model for analytics and business reports."""
    
    __tablename__ = "reports"
    
    business_id = db.Column(
        db.String(36),
        db.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id = db.Column(
        db.String(36),
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    name = db.Column(db.String(255), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    
    report_type = db.Column(db.String(50), nullable=False, index=True)
    report_format = db.Column(db.String(20), default="json", nullable=False, index=True)
    
    date_range_start = db.Column(db.DateTime, nullable=False, index=True)
    date_range_end = db.Column(db.DateTime, nullable=False, index=True)
    
    data = db.Column(db.JSON, default=dict, nullable=False)
    file_url = db.Column(db.String(500), nullable=True)
    
    is_scheduled = db.Column(db.Boolean, default=False, nullable=False, index=True)
    schedule_frequency = db.Column(db.String(20), nullable=True)
    next_run_at = db.Column(db.DateTime, nullable=True, index=True)
    
    status = db.Column(db.String(50), default="pending", nullable=False, index=True)
    error_message = db.Column(db.Text, nullable=True)
    
    completed_at = db.Column(db.DateTime, nullable=True, index=True)
    
    parameters = db.Column(db.JSON, default=dict, nullable=False)
    
    # Relationships
    business = db.relationship("Business", foreign_keys=[business_id], back_populates="reports")
    user = db.relationship("User")
    
    __table_args__ = (
        db.Index("idx_report_business_type", "business_id", "report_type"),
        db.Index("idx_report_date_range", "date_range_start", "date_range_end"),
        db.Index("idx_report_scheduled_next", "is_scheduled", "next_run_at"),
        db.Index("idx_report_status_date", "status", "created_at"),
    )
    
    TYPE_ANALYTICS = "analytics"
    TYPE_PERFORMANCE = "performance"
    TYPE_LEAD = "lead"
    TYPE_CONVERSION = "conversion"
    TYPE_ENGAGEMENT = "engagement"
    TYPE_REVENUE = "revenue"
    
    FORMAT_JSON = "json"
    FORMAT_CSV = "csv"
    FORMAT_PDF = "pdf"
    FORMAT_EXCEL = "excel"
    
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    
    def to_dict(self):
        """Convert report to dictionary."""
        data = super().to_dict()
        data.pop("is_deleted", None)
        data.pop("deleted_at", None)
        data.pop("data", None)
        return data