"""Repositories package for data access layer."""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional

from app import db

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Base repository with common CRUD operations."""
    
    model: T = None
    
    def get_by_id(self, id: str) -> Optional[T]:
        """Get entity by ID."""
        return self.model.query.filter_by(id=id).first()
    
    def get_all(self, limit: int = None, offset: int = None) -> List[T]:
        """Get all entities with optional pagination."""
        query = self.model.query
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        return query.all()
    
    def count(self) -> int:
        """Count all entities."""
        return self.model.query.count()
    
    def create(self, **kwargs) -> T:
        """Create a new entity."""
        entity = self.model(**kwargs)
        db.session.add(entity)
        db.session.commit()
        return entity
    
    def update(self, entity: T, **kwargs) -> T:
        """Update an entity."""
        for key, value in kwargs.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        db.session.commit()
        return entity
    
    def delete(self, entity: T) -> None:
        """Delete an entity."""
        db.session.delete(entity)
        db.session.commit()
    
    def save(self, entity: T) -> T:
        """Save an entity."""
        db.session.add(entity)
        db.session.commit()
        return entity


# Import Instagram repositories for easy access
from repositories.instagram_repository import (
    InstagramRepository,
    WebhookLogRepository,
    EventLogRepository,
)

__all__ = [
    "BaseRepository",
    "InstagramRepository",
    "WebhookLogRepository",
    "EventLogRepository",
]