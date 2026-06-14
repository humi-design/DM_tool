"""Resource model for educational and marketing content."""

from app import db
from models.base import BaseModel, SoftDeleteMixin


class Resource(BaseModel, SoftDeleteMixin):
    """Resource model for educational and marketing content."""
    
    __tablename__ = "resources"
    
    business_id = db.Column(
        db.String(36),
        db.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    title = db.Column(db.String(255), nullable=False, index=True)
    slug = db.Column(db.String(255), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    content = db.Column(db.Text, nullable=True)
    
    resource_type = db.Column(db.String(50), nullable=False, index=True)
    category = db.Column(db.String(100), nullable=True, index=True)
    tags = db.Column(db.JSON, default=list, nullable=False)
    
    thumbnail_url = db.Column(db.String(500), nullable=True)
    file_url = db.Column(db.String(500), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)
    file_type = db.Column(db.String(50), nullable=True)
    
    is_published = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_featured = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_premium = db.Column(db.Boolean, default=False, nullable=False, index=True)
    
    view_count = db.Column(db.Integer, default=0, nullable=False)
    download_count = db.Column(db.Integer, default=0, nullable=False)
    
    published_at = db.Column(db.DateTime, nullable=True, index=True)
    
    metadata_json = db.Column(db.JSON, default=dict, nullable=False)
    
    # Relationships
    business = db.relationship("Business", foreign_keys=[business_id], back_populates="resources")
    
    __table_args__ = (
        db.UniqueConstraint("business_id", "slug", name="uq_resource_business_slug"),
        db.Index("idx_resource_business_published", "business_id", "is_published"),
        db.Index("idx_resource_type_published", "resource_type", "is_published"),
        db.Index("idx_resource_featured", "is_featured", "is_published"),
    )
    
    def to_dict(self):
        """Convert resource to dictionary."""
        data = super().to_dict()
        data.pop("is_deleted", None)
        data.pop("deleted_at", None)
        return data