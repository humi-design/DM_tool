"""Comment model for Instagram comments and user discussions."""

from app import db
from models.base import BaseModel, SoftDeleteMixin


class Comment(BaseModel, SoftDeleteMixin):
    """Comment model for Instagram comments and user discussions."""
    
    __tablename__ = "comments"
    
    instagram_account_id = db.Column(
        db.String(36),
        db.ForeignKey("instagram_accounts.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    business_id = db.Column(
        db.String(36),
        db.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    user_id = db.Column(
        db.String(36),
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    instagram_comment_id = db.Column(db.String(100), nullable=True, index=True)
    parent_id = db.Column(
        db.String(36),
        db.ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    
    text = db.Column(db.Text, nullable=False)
    
    author_instagram_id = db.Column(db.String(100), nullable=True, index=True)
    author_username = db.Column(db.String(255), nullable=True, index=True)
    author_name = db.Column(db.String(255), nullable=True)
    author_avatar_url = db.Column(db.String(500), nullable=True)
    
    is_reply = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_spam = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_hidden = db.Column(db.Boolean, default=False, nullable=False, index=True)
    
    sentiment_score = db.Column(db.Float, nullable=True, index=True)
    auto_reply_enabled = db.Column(db.Boolean, default=False, nullable=False)
    auto_reply_text = db.Column(db.Text, nullable=True)
    
    timestamp = db.Column(db.DateTime, nullable=True, index=True)
    last_synced_at = db.Column(db.DateTime, nullable=True)
    
    reply_count = db.Column(db.Integer, default=0, nullable=False)
    like_count = db.Column(db.Integer, default=0, nullable=False)
    
    metadata_json = db.Column(db.JSON, default=dict, nullable=False)
    
    # Relationships
    instagram_account = db.relationship("InstagramAccount", foreign_keys=[instagram_account_id], back_populates="comments")
    business = db.relationship("Business", foreign_keys=[business_id], back_populates="comments")
    user = db.relationship("User")
    parent = db.relationship("Comment", remote_side="Comment.id", backref="replies")
    replies = db.relationship("Comment", backref="parent", remote_side="Comment.parent_id", lazy="dynamic")
    
    __table_args__ = (
        db.Index("idx_comment_instagram_parent", "instagram_account_id", "parent_id"),
        db.Index("idx_comment_timestamp", "timestamp"),
        db.Index("idx_comment_spam", "is_spam", "is_hidden"),
    )
    
    def to_dict(self):
        """Convert comment to dictionary."""
        data = super().to_dict()
        data.pop("is_deleted", None)
        data.pop("deleted_at", None)
        return data