"""Base model with common fields and mixins."""

from datetime import datetime
import uuid

from app import db


class BaseModel(db.Model):
    """Abstract base model with common fields."""
    
    __abstract__ = True
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def save(self):
        """Save the instance to the database."""
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        """Delete the instance from the database."""
        db.session.delete(self)
        db.session.commit()
    
    def update(self, **kwargs):
        """Update the instance with given kwargs."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        db.session.commit()
    
    def refresh(self):
        """Refresh the instance from the database."""
        db.session.refresh(self)
    
    @classmethod
    def find_by_id(cls, id):
        """Find a record by ID."""
        return cls.query.filter_by(id=id).first()
    
    @classmethod
    def find_all(cls, limit=None, offset=None):
        """Find all records with optional pagination."""
        query = cls.query
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        return query.all()
    
    @classmethod
    def count(cls):
        """Count all records."""
        return cls.query.count()


class TimestampMixin:
    """Mixin for timestamp fields."""
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        index=True
    )


class SoftDeleteMixin:
    """Mixin for soft delete functionality."""
    
    deleted_at = db.Column(db.DateTime, nullable=True, index=True)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False, index=True)
    
    def soft_delete(self):
        """Soft delete the record."""
        self.deleted_at = datetime.utcnow()
        self.is_deleted = True
        db.session.commit()
    
    def restore(self):
        """Restore a soft-deleted record."""
        self.deleted_at = None
        self.is_deleted = False
        db.session.commit()
    
    @classmethod
    def active(cls):
        """Query only active (non-deleted) records."""
        return cls.query.filter_by(is_deleted=False)


class UUIDPrimaryKeyMixin:
    """Mixin for UUID primary key."""
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))