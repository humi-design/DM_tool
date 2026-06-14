"""Organization model."""

from app import db
from models.base import BaseModel, SoftDeleteMixin


class Organization(BaseModel, SoftDeleteMixin):
    """Organization model for multi-tenancy."""
    
    __tablename__ = "organizations"
    
    name = db.Column(db.String(255), nullable=False, index=True)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    logo_url = db.Column(db.String(500), nullable=True)
    website = db.Column(db.String(500), nullable=True)
    
    owner_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    
    plan = db.Column(db.String(50), default="free", nullable=False)
    plan_expires_at = db.Column(db.DateTime, nullable=True)
    
    settings = db.Column(db.JSON, default=dict, nullable=False)
    metadata = db.Column(db.JSON, default=dict, nullable=False)
    
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_suspended = db.Column(db.Boolean, default=False, nullable=False)
    
    def to_dict(self):
        """Convert organization to dictionary."""
        data = super().to_dict()
        data.pop("is_deleted", None)
        return data
    
    @property
    def is_plan_active(self) -> bool:
        """Check if the organization has an active plan."""
        if self.plan == "free":
            return True
        if not self.plan_expires_at:
            return False
        from datetime import datetime
        return self.plan_expires_at > datetime.utcnow()


class OrganizationMember(BaseModel):
    """Organization membership model."""
    
    __tablename__ = "organization_members"
    
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id"), nullable=False)
    
    role = db.Column(db.String(50), default="member", nullable=False)
    permissions = db.Column(db.JSON, default=list, nullable=False)
    
    invited_by = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)
    joined_at = db.Column(db.DateTime, nullable=False)
    
    __table_args__ = (
        db.UniqueConstraint("user_id", "organization_id", name="uq_org_member"),
    )
    
    def to_dict(self):
        """Convert membership to dictionary."""
        return super().to_dict()