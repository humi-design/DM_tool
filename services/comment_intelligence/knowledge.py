"""Knowledge Retrieval Module - Intelligent knowledge base for responses.

This module provides a configurable knowledge base that can store
business information, FAQs, product details, and other resources
for intelligent response generation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
import json
import hashlib


@dataclass
class KnowledgeEntry:
    """A single knowledge base entry."""
    id: str
    category: str
    title: str
    content: str
    keywords: List[str] = field(default_factory=list)
    intent_types: List[str] = field(default_factory=list)
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    is_active: bool = True
    
    def matches_intent(self, intent: str) -> bool:
        """Check if this entry matches a specific intent."""
        return intent.lower() in [i.lower() for i in self.intent_types]
    
    def search_score(self, query: str) -> float:
        """Calculate relevance score for a search query."""
        query_lower = query.lower()
        score = 0.0
        
        # Exact match in title
        if query_lower in self.title.lower():
            score += 10.0
        
        # Exact match in content
        if query_lower in self.content.lower():
            score += 5.0
        
        # Keyword matches
        for keyword in self.keywords:
            if query_lower in keyword.lower():
                score += 3.0
        
        # Category match
        if query_lower in self.category.lower():
            score += 2.0
        
        # Priority boost
        score += self.priority * 0.1
        
        return score
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "category": self.category,
            "title": self.title,
            "content": self.content,
            "keywords": self.keywords,
            "intent_types": self.intent_types,
            "priority": self.priority,
            "metadata": self.metadata,
        }


@dataclass
class KnowledgeRetrievalResult:
    """Result from knowledge retrieval."""
    entries: List[KnowledgeEntry]
    relevance_scores: List[float]
    total_score: float
    query: str
    intent_filter: Optional[str] = None
    
    @property
    def best_match(self) -> Optional[KnowledgeEntry]:
        """Get the highest relevance entry."""
        if self.entries:
            best_idx = self.relevance_scores.index(max(self.relevance_scores))
            return self.entries[best_idx]
        return None
    
    def to_context_string(self) -> str:
        """Convert to a formatted string for AI prompts."""
        if not self.entries:
            return "No relevant knowledge base entries found."
        
        sections = ["## Relevant Knowledge Base Information\n"]
        
        for entry, score in zip(self.entries, self.relevance_scores):
            sections.append(f"### {entry.title} (relevance: {score:.2f})")
            sections.append(f"Category: {entry.category}")
            sections.append(entry.content)
            sections.append("")
        
        return "\n".join(sections)


class KnowledgeBase:
    """Configurable knowledge base for comment processing.
    
    This class manages a searchable knowledge base with entries
    that can be categorized by intent, keywords, and content.
    """
    
    def __init__(self):
        """Initialize the knowledge base."""
        self._entries: Dict[str, KnowledgeEntry] = {}
        self._category_index: Dict[str, List[str]] = {}
        self._intent_index: Dict[str, List[str]] = {}
        self._initialize_default_entries()
    
    def _initialize_default_entries(self) -> None:
        """Initialize with default knowledge base entries."""
        default_entries = [
            # Resource-related entries
            KnowledgeEntry(
                id="menu_request",
                category="resources",
                title="Menu and Catalog",
                content="Our full menu/catalog is available on our website. Would you like me to send you the link?",
                keywords=["menu", "catalog", "items", "options", "list"],
                intent_types=["resource"],
                priority=10
            ),
            KnowledgeEntry(
                id="brochure_request",
                category="resources",
                title="Brochure and Documents",
                content="I'd be happy to share our brochure with you! What's the best email to send it to?",
                keywords=["brochure", "flyer", "document", "pdf", "catalog"],
                intent_types=["resource"],
                priority=9
            ),
            KnowledgeEntry(
                id="pricing_info",
                category="resources",
                title="Pricing Information",
                content="Our pricing varies based on your needs. Would you like a personalized quote?",
                keywords=["price", "cost", "pricing", "quote", "estimate", "fee"],
                intent_types=["price", "resource"],
                priority=10
            ),
            
            # Interest-related entries
            KnowledgeEntry(
                id="interested_response",
                category="engagement",
                title="Interest Acknowledgment",
                content="Thank you for your interest! I'd love to tell you more about what we offer.",
                keywords=["interested", "want", "love", "amazing"],
                intent_types=["interest"],
                priority=8
            ),
            
            # Booking-related entries
            KnowledgeEntry(
                id="booking_request",
                category="bookings",
                title="Appointment Booking",
                content="I'd be happy to help you book an appointment. What date and time works best for you?",
                keywords=["book", "appointment", "schedule", "reserve", "time slot"],
                intent_types=["booking"],
                priority=10
            ),
            
            # Support-related entries
            KnowledgeEntry(
                id="support_response",
                category="support",
                title="Support Assistance",
                content="I'm here to help! Could you please provide more details about your issue?",
                keywords=["help", "support", "problem", "issue", "not working"],
                intent_types=["support"],
                priority=10
            ),
            
            # Order-related entries
            KnowledgeEntry(
                id="order_guide",
                category="orders",
                title="How to Order",
                content="You can place an order directly through our website or app. Need help with the process?",
                keywords=["order", "buy", "purchase", "checkout"],
                intent_types=["order"],
                priority=10
            ),
            
            # Greeting entries
            KnowledgeEntry(
                id="greeting_response",
                category="general",
                title="Friendly Greeting",
                content="Hello! Thanks for reaching out. How can I help you today?",
                keywords=["hi", "hello", "hey", "good morning", "good afternoon"],
                intent_types=["greeting"],
                priority=5
            ),
            
            # FAQ entries
            KnowledgeEntry(
                id="general_faq",
                category="faq",
                title="Common Questions",
                content="Common questions and answers about our products and services.",
                keywords=["what", "how", "when", "where", "faq"],
                intent_types=["question"],
                priority=7
            ),
        ]
        
        for entry in default_entries:
            self.add_entry(entry)
    
    def add_entry(self, entry: KnowledgeEntry) -> None:
        """Add a knowledge base entry.
        
        Args:
            entry: KnowledgeEntry to add
        """
        self._entries[entry.id] = entry
        
        # Update category index
        if entry.category not in self._category_index:
            self._category_index[entry.category] = []
        self._category_index[entry.category].append(entry.id)
        
        # Update intent index
        for intent in entry.intent_types:
            if intent not in self._intent_index:
                self._intent_index[intent] = []
            self._intent_index[intent].append(entry.id)
    
    def remove_entry(self, entry_id: str) -> bool:
        """Remove a knowledge base entry.
        
        Args:
            entry_id: ID of entry to remove
            
        Returns:
            True if removed, False if not found
        """
        if entry_id not in self._entries:
            return False
        
        entry = self._entries[entry_id]
        
        # Remove from indexes
        if entry.category in self._category_index:
            self._category_index[entry.category].remove(entry_id)
        
        for intent in entry.intent_types:
            if intent in self._intent_index:
                self._intent_index[intent].remove(entry_id)
        
        del self._entries[entry_id]
        return True
    
    def get_entry(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """Get a specific knowledge base entry.
        
        Args:
            entry_id: ID of entry to retrieve
            
        Returns:
            KnowledgeEntry if found, None otherwise
        """
        return self._entries.get(entry_id)
    
    def get_entries_by_category(self, category: str) -> List[KnowledgeEntry]:
        """Get all entries in a category.
        
        Args:
            category: Category name
            
        Returns:
            List of entries in the category
        """
        entry_ids = self._category_index.get(category, [])
        return [self._entries[eid] for eid in entry_ids if eid in self._entries]
    
    def get_entries_by_intent(self, intent: str) -> List[KnowledgeEntry]:
        """Get all entries that match an intent.
        
        Args:
            intent: Intent type string
            
        Returns:
            List of matching entries
        """
        entry_ids = self._intent_index.get(intent, [])
        return [self._entries[eid] for eid in entry_ids if eid in self._entries]
    
    def search(
        self,
        query: str,
        intent_filter: Optional[str] = None,
        limit: int = 5,
        min_score: float = 0.0
    ) -> KnowledgeRetrievalResult:
        """Search the knowledge base.
        
        Args:
            query: Search query
            intent_filter: Optional intent to filter by
            limit: Maximum number of results
            min_score: Minimum relevance score threshold
            
        Returns:
            KnowledgeRetrievalResult with matched entries
        """
        candidates = []
        
        # Get candidates based on intent filter
        if intent_filter:
            candidates = self.get_entries_by_intent(intent_filter)
        else:
            candidates = list(self._entries.values())
        
        # Score each candidate
        scored_entries = []
        for entry in candidates:
            if not entry.is_active:
                continue
            score = entry.search_score(query)
            if score >= min_score:
                scored_entries.append((entry, score))
        
        # Sort by score and take top results
        scored_entries.sort(key=lambda x: -x[1])
        top_entries = scored_entries[:limit]
        
        return KnowledgeRetrievalResult(
            entries=[e[0] for e in top_entries],
            relevance_scores=[e[1] for e in top_entries],
            total_score=sum(e[1] for e in top_entries),
            query=query,
            intent_filter=intent_filter
        )
    
    def retrieve_for_intent(
        self,
        intent: str,
        context: Optional[Dict[str, Any]] = None,
        limit: int = 3
    ) -> KnowledgeRetrievalResult:
        """Retrieve knowledge entries specifically for an intent.
        
        Args:
            intent: Intent type
            context: Optional context for smarter retrieval
            limit: Maximum number of results
            
        Returns:
            KnowledgeRetrievalResult with matched entries
        """
        entries = self.get_entries_by_intent(intent)
        
        if not entries:
            # Fallback to general search
            return self.search(intent, limit=limit)
        
        # Sort by priority and return top results
        entries.sort(key=lambda e: -e.priority)
        
        return KnowledgeRetrievalResult(
            entries=entries[:limit],
            relevance_scores=[e.priority * 1.0 for e in entries[:limit]],
            total_score=sum(e.priority for e in entries[:limit]),
            query=intent,
            intent_filter=intent
        )
    
    def update_entry(self, entry_id: str, updates: Dict[str, Any]) -> bool:
        """Update a knowledge base entry.
        
        Args:
            entry_id: ID of entry to update
            updates: Dictionary of field updates
            
        Returns:
            True if updated, False if not found
        """
        if entry_id not in self._entries:
            return False
        
        entry = self._entries[entry_id]
        
        for key, value in updates.items():
            if hasattr(entry, key):
                setattr(entry, key, value)
        
        entry.updated_at = datetime.utcnow()
        return True
    
    def export_entries(self) -> List[Dict[str, Any]]:
        """Export all entries as dictionaries."""
        return [entry.to_dict() for entry in self._entries.values()]
    
    def import_entries(self, entries: List[Dict[str, Any]]) -> int:
        """Import entries from dictionaries.
        
        Args:
            entries: List of entry dictionaries
            
        Returns:
            Number of entries imported
        """
        count = 0
        for entry_data in entries:
            try:
                entry = KnowledgeEntry(
                    id=entry_data["id"],
                    category=entry_data["category"],
                    title=entry_data["title"],
                    content=entry_data["content"],
                    keywords=entry_data.get("keywords", []),
                    intent_types=entry_data.get("intent_types", []),
                    priority=entry_data.get("priority", 0),
                    metadata=entry_data.get("metadata", {}),
                )
                self.add_entry(entry)
                count += 1
            except KeyError:
                continue
        
        return count
    
    @property
    def entry_count(self) -> int:
        """Get total number of entries."""
        return len(self._entries)
    
    @property
    def categories(self) -> List[str]:
        """Get list of all categories."""
        return list(self._category_index.keys())
    
    @property
    def intents(self) -> List[str]:
        """Get list of all intent types."""
        return list(self._intent_index.keys())