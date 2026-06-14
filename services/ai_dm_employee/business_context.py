"""Business Context Manager - Loads and manages business context from various sources."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from enum import Enum
import re
import json


class KnowledgeSource(Enum):
    """Types of knowledge sources."""
    WEBSITE = "website"
    PDF = "pdf"
    BROCHURE = "brochure"
    CATALOG = "catalog"
    MENU = "menu"
    FAQ = "faq"
    PORTFOLIO = "portfolio"
    GITHUB = "github"
    YOUTUBE = "youtube"
    MANUAL = "manual"
    NOTION = "notion"
    DOCS = "docs"


@dataclass
class KnowledgeItem:
    """A single piece of knowledge from a source."""
    id: str
    source: KnowledgeSource
    source_name: str
    content: str
    title: str = ""
    url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    category: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    priority: int = 0  # Higher = more important
    verified: bool = True


@dataclass
class BusinessContext:
    """Complete business context for a business."""
    business_id: str
    business_name: str
    business_type: str = ""
    industry: str = ""
    
    # Basic info
    description: str = ""
    website: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    
    # Products/Services
    products: List[Dict[str, Any]] = field(default_factory=list)
    services: List[Dict[str, Any]] = field(default_factory=list)
    pricing: Dict[str, Any] = field(default_factory=dict)
    
    # Knowledge base
    faq: List[Dict[str, str]] = field(default_factory=list)
    knowledge_items: List[KnowledgeItem] = field(default_factory=list)
    
    # Social/Portfolio
    portfolio: List[Dict[str, Any]] = field(default_factory=list)
    social_links: Dict[str, str] = field(default_factory=dict)
    
    # Team/Company info
    team: List[Dict[str, str]] = field(default_factory=list)
    company_values: List[str] = field(default_factory=list)
    policies: Dict[str, str] = field(default_factory=dict)
    
    # AI configuration
    ai_personality: str = "professional"
    ai_tone: str = "friendly"
    ai_response_style: str = "helpful"
    
    # Last updated
    last_synced: datetime = field(default_factory=datetime.utcnow)
    
    # Metadata
    metadata_json: Dict[str, Any] = field(default_factory=dict)


class BusinessContextManager:
    """Manages business context from multiple sources.
    
    Responsibilities:
    - Load and index knowledge from various sources
    - Maintain FAQ knowledge
    - Track product/service catalog
    - Manage portfolio and social links
    - Provide context for AI responses
    """
    
    def __init__(self):
        """Initialize the business context manager."""
        self._contexts: Dict[str, BusinessContext] = {}
        self._knowledge_index: Dict[str, List[str]] = {}  # business_id -> [knowledge_item_ids]
        self._faq_index: Dict[str, Dict[str, str]] = {}  # business_id -> {question -> answer}
    
    def load_context_from_business(
        self,
        business: Any,
        include_resources: bool = True,
    ) -> BusinessContext:
        """Load business context from a Business model instance.
        
        Args:
            business: Business model instance
            include_resources: Whether to load associated resources
            
        Returns:
            BusinessContext object
        """
        context = BusinessContext(
            business_id=str(business.id),
            business_name=business.name,
            business_type=business.business_type or "",
            industry=business.industry or "",
            description=business.description or "",
            website=business.website or "",
            email=business.email or "",
            phone=business.phone or "",
            address=business.address or "",
            metadata_json=business.metadata_json or {},
        )
        
        self._contexts[context.business_id] = context
        return context
    
    def create_context_from_dict(
        self,
        business_id: str,
        data: Dict[str, Any],
    ) -> BusinessContext:
        """Create business context from a dictionary.
        
        Args:
            business_id: Business identifier
            data: Business data dictionary
            
        Returns:
            BusinessContext object
        """
        # Handle nested knowledge items
        knowledge_items = []
        if "knowledge_items" in data:
            for item_data in data["knowledge_items"]:
                if isinstance(item_data, dict):
                    knowledge_items.append(KnowledgeItem(
                        id=item_data.get("id", ""),
                        source=KnowledgeSource(item_data.get("source", "manual")),
                        source_name=item_data.get("source_name", ""),
                        content=item_data.get("content", ""),
                        title=item_data.get("title", ""),
                        url=item_data.get("url"),
                        metadata=item_data.get("metadata", {}),
                        tags=item_data.get("tags", []),
                        category=item_data.get("category"),
                    ))
        
        context = BusinessContext(
            business_id=business_id,
            business_name=data.get("name", ""),
            business_type=data.get("business_type", ""),
            industry=data.get("industry", ""),
            description=data.get("description", ""),
            website=data.get("website", ""),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            address=data.get("address", ""),
            products=data.get("products", []),
            services=data.get("services", []),
            pricing=data.get("pricing", {}),
            faq=data.get("faq", []),
            knowledge_items=knowledge_items,
            portfolio=data.get("portfolio", []),
            social_links=data.get("social_links", {}),
            team=data.get("team", []),
            company_values=data.get("company_values", []),
            policies=data.get("policies", {}),
            ai_personality=data.get("ai_personality", "professional"),
            ai_tone=data.get("ai_tone", "friendly"),
            ai_response_style=data.get("ai_response_style", "helpful"),
            metadata_json=data.get("metadata", {}),
        )
        
        self._contexts[business_id] = context
        self._index_knowledge(business_id)
        self._index_faq(business_id)
        
        return context
    
    def _index_knowledge(self, business_id: str) -> None:
        """Index knowledge items for quick lookup.
        
        Args:
            business_id: Business to index
        """
        context = self._contexts.get(business_id)
        if not context:
            return
        
        self._knowledge_index[business_id] = []
        
        for item in context.knowledge_items:
            self._knowledge_index[business_id].append(item.id)
            
            # Index by tags
            for tag in item.tags:
                tag_key = f"tag:{tag}"
                if tag_key not in self._knowledge_index:
                    self._knowledge_index[tag_key] = []
                self._knowledge_index[tag_key].append(item.id)
            
            # Index by category
            if item.category:
                cat_key = f"category:{item.category}"
                if cat_key not in self._knowledge_index:
                    self._knowledge_index[cat_key] = []
                self._knowledge_index[cat_key].append(item.id)
    
    def _index_faq(self, business_id: str) -> None:
        """Index FAQ items for quick lookup.
        
        Args:
            business_id: Business to index
        """
        context = self._contexts.get(business_id)
        if not context:
            return
        
        self._faq_index[business_id] = {}
        
        for faq in context.faq:
            question = faq.get("question", "").lower().strip()
            answer = faq.get("answer", "")
            if question and answer:
                self._faq_index[business_id][question] = answer
    
    def get_context(self, business_id: str) -> Optional[BusinessContext]:
        """Get business context.
        
        Args:
            business_id: Business identifier
            
        Returns:
            BusinessContext or None
        """
        return self._contexts.get(business_id)
    
    def update_context(
        self,
        business_id: str,
        updates: Dict[str, Any],
    ) -> bool:
        """Update business context.
        
        Args:
            business_id: Business to update
            updates: Dictionary of updates
            
        Returns:
            True if updated successfully
        """
        context = self._contexts.get(business_id)
        if not context:
            return False
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(context, key):
                setattr(context, key, value)
        
        context.last_synced = datetime.utcnow()
        return True
    
    def add_knowledge_item(
        self,
        business_id: str,
        item: KnowledgeItem,
    ) -> bool:
        """Add a knowledge item to business context.
        
        Args:
            business_id: Business to add to
            item: Knowledge item to add
            
        Returns:
            True if added successfully
        """
        context = self._contexts.get(business_id)
        if not context:
            return False
        
        context.knowledge_items.append(item)
        self._index_knowledge(business_id)
        return True
    
    def search_knowledge(
        self,
        business_id: str,
        query: str,
        limit: int = 5,
    ) -> List[KnowledgeItem]:
        """Search knowledge base.
        
        Args:
            business_id: Business to search in
            query: Search query
            limit: Maximum results
            
        Returns:
            List of matching knowledge items
        """
        context = self._contexts.get(business_id)
        if not context:
            return []
        
        query_lower = query.lower()
        results = []
        
        for item in context.knowledge_items:
            score = 0
            
            # Title match (highest priority)
            if query_lower in item.title.lower():
                score += 10
            
            # Content match
            if query_lower in item.content.lower():
                score += 5
            
            # Tag match
            for tag in item.tags:
                if query_lower in tag.lower():
                    score += 3
            
            # Exact content match (highest priority)
            if query_lower == item.content.lower()[:len(query_lower)]:
                score += 15
            
            if score > 0:
                results.append((score, item))
        
        # Sort by score and return top results
        results.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in results[:limit]]
    
    def find_faq_answer(
        self,
        business_id: str,
        question: str,
    ) -> Optional[str]:
        """Find FAQ answer for a question.
        
        Args:
            business_id: Business to search in
            question: Question to find answer for
            
        Returns:
            Answer string or None
        """
        faq_index = self._faq_index.get(business_id, {})
        question_lower = question.lower().strip()
        
        # Exact match
        if question_lower in faq_index:
            return faq_index[question_lower]
        
        # Partial match
        for faq_question, answer in faq_index.items():
            if question_lower in faq_question or faq_question in question_lower:
                return answer
        
        # Keyword match
        question_words = set(question_lower.split())
        best_match = None
        best_score = 0
        
        for faq_question, answer in faq_index.items():
            faq_words = set(faq_question.split())
            overlap = len(question_words & faq_words)
            if overlap > best_score and overlap >= 2:
                best_score = overlap
                best_match = answer
        
        return best_match
    
    def get_products(
        self,
        business_id: str,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get products for a business.
        
        Args:
            business_id: Business identifier
            category: Optional category filter
            
        Returns:
            List of products
        """
        context = self._contexts.get(business_id)
        if not context:
            return []
        
        products = context.products
        if category:
            products = [p for p in products if p.get("category") == category]
        
        return products
    
    def get_services(
        self,
        business_id: str,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get services for a business.
        
        Args:
            business_id: Business identifier
            category: Optional category filter
            
        Returns:
            List of services
        """
        context = self._contexts.get(business_id)
        if not context:
            return []
        
        services = context.services
        if category:
            services = [s for s in services if s.get("category") == category]
        
        return services
    
    def get_pricing(
        self,
        business_id: str,
        item_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get pricing information.
        
        Args:
            business_id: Business identifier
            item_id: Optional specific item ID
            
        Returns:
            Pricing data or None
        """
        context = self._contexts.get(business_id)
        if not context:
            return None
        
        if item_id:
            return context.pricing.get(item_id)
        
        return context.pricing
    
    def build_system_prompt(
        self,
        business_id: str,
        include_products: bool = True,
        include_faq: bool = True,
        include_policies: bool = True,
    ) -> str:
        """Build a system prompt from business context.
        
        Args:
            business_id: Business to build prompt for
            include_products: Include product info
            include_faq: Include FAQ
            include_policies: Include policies
            
        Returns:
            Formatted system prompt
        """
        context = self._contexts.get(business_id)
        if not context:
            return ""
        
        parts = []
        
        # Business info
        parts.append(f"You are representing: {context.business_name}")
        if context.description:
            parts.append(f"About: {context.description}")
        
        # Industry
        if context.industry:
            parts.append(f"Industry: {context.industry}")
        
        # Contact info
        contact_info = []
        if context.website:
            contact_info.append(f"Website: {context.website}")
        if context.email:
            contact_info.append(f"Email: {context.email}")
        if context.phone:
            contact_info.append(f"Phone: {context.phone}")
        if contact_info:
            parts.append("Contact: " + ", ".join(contact_info))
        
        # Products/Services
        if include_products:
            if context.products:
                product_names = [p.get("name", "") for p in context.products[:5]]
                parts.append(f"Products: {', '.join(filter(None, product_names))}")
            
            if context.services:
                service_names = [s.get("name", "") for s in context.services[:5]]
                parts.append(f"Services: {', '.join(filter(None, service_names))}")
        
        # FAQ
        if include_faq and context.faq:
            parts.append("\nFrequently Asked Questions:")
            for faq in context.faq[:10]:
                parts.append(f"Q: {faq.get('question', '')}")
                parts.append(f"A: {faq.get('answer', '')}")
        
        # Policies
        if include_policies and context.policies:
            parts.append("\nPolicies:")
            for policy_name, policy_content in context.policies.items():
                parts.append(f"{policy_name}: {policy_content}")
        
        # Company values
        if context.company_values:
            parts.append(f"\nCompany Values: {', '.join(context.company_values)}")
        
        # AI personality
        parts.append(f"\nYour personality: {context.ai_personality}")
        parts.append(f"Tone: {context.ai_tone}")
        
        return "\n".join(parts)
    
    def get_all_business_ids(self) -> List[str]:
        """Get all business IDs with loaded context.
        
        Returns:
            List of business IDs
        """
        return list(self._contexts.keys())
    
    def remove_context(self, business_id: str) -> bool:
        """Remove business context.
        
        Args:
            business_id: Business to remove
            
        Returns:
            True if removed
        """
        if business_id in self._contexts:
            del self._contexts[business_id]
        if business_id in self._knowledge_index:
            del self._knowledge_index[business_id]
        if business_id in self._faq_index:
            del self._faq_index[business_id]
        return True
