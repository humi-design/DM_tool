"""Knowledge Base Service - Vector search, document indexing, and retrieval."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple, Callable
from enum import Enum
import hashlib
import re
import math


class DocumentType(Enum):
    """Types of documents in knowledge base."""
    TEXT = "text"
    PDF = "pdf"
    WEBPAGE = "webpage"
    FAQ = "faq"
    PRODUCT = "product"
    SERVICE = "service"
    POLICY = "policy"
    MANUAL = "manual"


@dataclass
class Document:
    """A document in the knowledge base."""
    id: str
    content: str
    doc_type: DocumentType
    title: str = ""
    url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    source: str = ""  # e.g., "website", "pdf_upload", "manual"
    chunk_id: Optional[str] = None  # For chunked documents
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    # Embedding cache
    _embedding: Optional[List[float]] = None
    
    def get_embedding(self) -> Optional[List[float]]:
        """Get cached embedding."""
        return self._embedding
    
    def set_embedding(self, embedding: List[float]) -> None:
        """Set embedding."""
        self._embedding = embedding


@dataclass
class SearchResult:
    """Result from a knowledge base search."""
    document: Document
    score: float
    highlights: List[str] = field(default_factory=list)
    distance: float = 0.0


class SimpleVectorStore:
    """Simple in-memory vector store using TF-IDF for embeddings.
    
    Note: In production, use a proper vector database like Pinecone, Weaviate,
    or Qdrant for better performance and scalability.
    """
    
    def __init__(self):
        """Initialize the vector store."""
        self._documents: Dict[str, Document] = {}
        self._index: Dict[str, Dict[str, float]] = {}  # doc_id -> {term -> tfidf}
        self._document_count: int = 0
        self._idf: Dict[str, float] = {}  # term -> idf score
    
    def add_document(self, document: Document) -> None:
        """Add a document to the store.
        
        Args:
            document: Document to add
        """
        self._documents[document.id] = document
        self._index_document(document)
        self._document_count += 1
        self._update_idf()
    
    def _index_document(self, document: Document) -> None:
        """Index a single document.
        
        Args:
            document: Document to index
        """
        terms = self._tokenize(document.content)
        term_freq = {}
        
        for term in terms:
            term_freq[term] = term_freq.get(term, 0) + 1
        
        # Normalize by document length
        if terms:
            for term in term_freq:
                term_freq[term] /= len(terms)
        
        self._index[document.id] = term_freq
    
    def _update_idf(self) -> None:
        """Update IDF scores for all terms."""
        doc_count = max(1, self._document_count)
        
        # Count documents containing each term
        term_doc_count: Dict[str, int] = {}
        for doc_id, term_freq in self._index.items():
            for term in term_freq:
                term_doc_count[term] = term_doc_count.get(term, 0) + 1
        
        # Calculate IDF
        for term, count in term_doc_count.items():
            self._idf[term] = math.log(doc_count / (1 + count))
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into terms.
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of terms
        """
        # Lowercase and split on non-alphanumeric
        tokens = re.findall(r'\b[a-zA-Z0-9]+\b', text.lower())
        
        # Remove very short tokens and stopwords
        stopwords = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'will', 'with', 'i', 'you', 'we', 'they', 'this',
            'but', 'not', 'or', 'if', 'so', 'what', 'how', 'when', 'where',
            'why', 'can', 'could', 'would', 'should', 'may', 'might', 'must',
        }
        
        return [t for t in tokens if len(t) > 2 and t not in stopwords]
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        doc_type_filter: Optional[DocumentType] = None,
    ) -> List[Tuple[Document, float]]:
        """Search documents by query.
        
        Args:
            query: Search query
            top_k: Number of results to return
            doc_type_filter: Optional filter by document type
            
        Returns:
            List of (Document, score) tuples
        """
        query_terms = self._tokenize(query)
        if not query_terms:
            return []
        
        # Calculate query TF-IDF
        query_tf: Dict[str, float] = {}
        for term in query_terms:
            query_tf[term] = query_tf.get(term, 0) + 1
        
        # Normalize
        if query_terms:
            for term in query_tf:
                query_tf[term] /= len(query_terms)
        
        # Calculate cosine similarity
        scores: Dict[str, float] = {}
        for doc_id, doc_term_freq in self._index.items():
            # Filter by doc type if specified
            if doc_type_filter:
                doc = self._documents.get(doc_id)
                if not doc or doc.doc_type != doc_type_filter:
                    continue
            
            # Calculate dot product
            dot_product = 0.0
            query_magnitude = 0.0
            doc_magnitude = 0.0
            
            for term, qtf in query_tf.items():
                idf = self._idf.get(term, 0)
                qtf_idf = qtf * idf
                query_magnitude += qtf_idf ** 2
                
                dtf = doc_term_freq.get(term, 0) * idf
                dot_product += qtf_idf * dtf
                doc_magnitude += dtf ** 2
            
            if query_magnitude > 0 and doc_magnitude > 0:
                cosine_sim = dot_product / (math.sqrt(query_magnitude) * math.sqrt(doc_magnitude))
                scores[doc_id] = cosine_sim
        
        # Sort by score
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        # Return top results
        results = []
        for doc_id, score in sorted_scores[:top_k]:
            doc = self._documents.get(doc_id)
            if doc:
                results.append((doc, score))
        
        return results
    
    def get_document(self, doc_id: str) -> Optional[Document]:
        """Get a document by ID.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document or None
        """
        return self._documents.get(doc_id)
    
    def delete_document(self, doc_id: str) -> bool:
        """Delete a document.
        
        Args:
            doc_id: Document ID
            
        Returns:
            True if deleted
        """
        if doc_id in self._documents:
            del self._documents[doc_id]
        if doc_id in self._index:
            del self._index[doc_id]
        self._document_count = max(0, self._document_count - 1)
        return True
    
    def count(self) -> int:
        """Get number of documents."""
        return len(self._documents)


class KnowledgeBaseService:
    """Service for managing knowledge base with vector search.
    
    Responsibilities:
    - Index documents from various sources
    - Perform semantic search
    - Provide context for AI responses
    - Track document freshness
    """
    
    def __init__(self):
        """Initialize the knowledge base service."""
        self._stores: Dict[str, SimpleVectorStore] = {}  # business_id -> store
        self._business_documents: Dict[str, Dict[str, Document]] = {}  # business_id -> {doc_id -> doc}
    
    def get_or_create_store(self, business_id: str) -> SimpleVectorStore:
        """Get or create a vector store for a business.
        
        Args:
            business_id: Business identifier
            
        Returns:
            Vector store for the business
        """
        if business_id not in self._stores:
            self._stores[business_id] = SimpleVectorStore()
            self._business_documents[business_id] = {}
        return self._stores[business_id]
    
    def index_document(
        self,
        business_id: str,
        content: str,
        doc_type: DocumentType,
        title: str = "",
        url: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        source: str = "",
    ) -> str:
        """Index a document for a business.
        
        Args:
            business_id: Business identifier
            content: Document content
            doc_type: Type of document
            title: Document title
            url: Source URL
            tags: Document tags
            metadata: Additional metadata
            source: Document source
            
        Returns:
            Document ID
        """
        # Generate document ID
        doc_id = hashlib.md5(
            f"{business_id}:{content[:100]}".encode()
        ).hexdigest()[:16]
        
        document = Document(
            id=doc_id,
            content=content,
            doc_type=doc_type,
            title=title,
            url=url,
            tags=tags or [],
            metadata=metadata or {},
            source=source,
        )
        
        store = self.get_or_create_store(business_id)
        store.add_document(document)
        self._business_documents[business_id][doc_id] = document
        
        return doc_id
    
    def index_text_content(
        self,
        business_id: str,
        texts: List[Dict[str, str]],
        doc_type: DocumentType = DocumentType.TEXT,
        source: str = "",
    ) -> List[str]:
        """Index multiple text items.
        
        Args:
            business_id: Business identifier
            texts: List of text items with 'content' and optional 'title'
            doc_type: Type of documents
            source: Document source
            
        Returns:
            List of document IDs
        """
        doc_ids = []
        for text in texts:
            doc_id = self.index_document(
                business_id=business_id,
                content=text.get("content", ""),
                doc_type=doc_type,
                title=text.get("title", ""),
                tags=text.get("tags", []),
                metadata=text.get("metadata", {}),
                source=source,
            )
            doc_ids.append(doc_id)
        return doc_ids
    
    def index_faq(
        self,
        business_id: str,
        faq_items: List[Dict[str, str]],
    ) -> List[str]:
        """Index FAQ items.
        
        Args:
            business_id: Business identifier
            faq_items: List of FAQ items with 'question' and 'answer'
            
        Returns:
            List of document IDs
        """
        return self.index_text_content(
            business_id=business_id,
            texts=[
                {
                    "content": f"Q: {faq.get('question', '')}\nA: {faq.get('answer', '')}",
                    "title": faq.get("question", ""),
                    "tags": ["faq"],
                }
                for faq in faq_items
            ],
            doc_type=DocumentType.FAQ,
            source="faq",
        )
    
    def index_products(
        self,
        business_id: str,
        products: List[Dict[str, Any]],
    ) -> List[str]:
        """Index product catalog.
        
        Args:
            business_id: Business identifier
            products: List of product dictionaries
            
        Returns:
            List of document IDs
        """
        def format_product(p: Dict[str, Any]) -> str:
            parts = []
            if name := p.get("name"):
                parts.append(f"Product: {name}")
            if desc := p.get("description"):
                parts.append(desc)
            if price := p.get("price"):
                parts.append(f"Price: {price}")
            if features := p.get("features"):
                if isinstance(features, list):
                    parts.append(f"Features: {', '.join(features)}")
            return "\n".join(parts)
        
        return self.index_text_content(
            business_id=business_id,
            texts=[
                {
                    "content": format_product(p),
                    "title": p.get("name", ""),
                    "tags": ["product", p.get("category", "general")],
                    "metadata": {"product_id": p.get("id")},
                }
                for p in products
            ],
            doc_type=DocumentType.PRODUCT,
            source="catalog",
        )
    
    def index_website_content(
        self,
        business_id: str,
        content: str,
        url: str,
        title: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Index website content.
        
        Args:
            business_id: Business identifier
            content: Website content
            url: Website URL
            title: Page title
            metadata: Additional metadata
            
        Returns:
            Document ID
        """
        return self.index_document(
            business_id=business_id,
            content=content,
            doc_type=DocumentType.WEBPAGE,
            title=title,
            url=url,
            source="website",
            metadata=metadata or {},
        )
    
    def index_pdf_content(
        self,
        business_id: str,
        content: str,
        filename: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Index PDF content.
        
        Args:
            business_id: Business identifier
            content: Extracted PDF content
            filename: Original filename
            metadata: Additional metadata
            
        Returns:
            Document ID
        """
        return self.index_document(
            business_id=business_id,
            content=content,
            doc_type=DocumentType.PDF,
            title=filename,
            source="pdf",
            metadata=metadata or {},
        )
    
    def search(
        self,
        business_id: str,
        query: str,
        top_k: int = 5,
        doc_type: Optional[DocumentType] = None,
        min_score: float = 0.1,
    ) -> List[SearchResult]:
        """Search knowledge base.
        
        Args:
            business_id: Business identifier
            query: Search query
            top_k: Maximum results
            doc_type: Optional document type filter
            min_score: Minimum relevance score
            
        Returns:
            List of search results
        """
        store = self._stores.get(business_id)
        if not store:
            return []
        
        results = store.search(
            query=query,
            top_k=top_k * 2,  # Get more to filter
            doc_type_filter=doc_type,
        )
        
        search_results = []
        for doc, score in results:
            if score >= min_score:
                highlights = self._extract_highlights(doc.content, query)
                search_results.append(SearchResult(
                    document=doc,
                    score=score,
                    highlights=highlights,
                    distance=1 - score,
                ))
        
        return search_results[:top_k]
    
    def _extract_highlights(
        self,
        content: str,
        query: str,
        context_chars: int = 100,
    ) -> List[str]:
        """Extract highlighted snippets from content.
        
        Args:
            content: Document content
            query: Search query
            context_chars: Characters of context around match
            
        Returns:
            List of highlight snippets
        """
        highlights = []
        query_terms = query.lower().split()
        
        # Find sentences containing query terms
        sentences = content.split('.')
        for sentence in sentences:
            sentence_lower = sentence.lower()
            for term in query_terms:
                if term in sentence_lower:
                    # Trim to context
                    if len(sentence) > context_chars * 2:
                        start = max(0, sentence.lower().find(term) - context_chars)
                        end = min(len(sentence), start + context_chars * 2)
                        sentence = ("..." if start > 0 else "") + sentence[start:end] + ("..." if end < len(sentence) else "")
                    highlights.append(sentence.strip())
                    break
        
        return highlights[:3]  # Max 3 highlights
    
    def get_relevant_context(
        self,
        business_id: str,
        query: str,
        max_chars: int = 2000,
    ) -> str:
        """Get relevant context for AI prompt.
        
        Args:
            business_id: Business identifier
            query: Query to find context for
            max_chars: Maximum characters to return
            
        Returns:
            Concatenated relevant context
        """
        results = self.search(business_id, query, top_k=5, min_score=0.05)
        
        context_parts = []
        total_chars = 0
        
        for result in results:
            content = result.document.content
            if total_chars + len(content) <= max_chars:
                context_parts.append(content)
                total_chars += len(content)
            else:
                # Add partial content
                remaining = max_chars - total_chars
                if remaining > 100:
                    context_parts.append(content[:remaining] + "...")
                break
        
        return "\n\n---\n\n".join(context_parts)
    
    def get_document(self, business_id: str, doc_id: str) -> Optional[Document]:
        """Get a specific document.
        
        Args:
            business_id: Business identifier
            doc_id: Document ID
            
        Returns:
            Document or None
        """
        docs = self._business_documents.get(business_id, {})
        return docs.get(doc_id)
    
    def delete_document(self, business_id: str, doc_id: str) -> bool:
        """Delete a document.
        
        Args:
            business_id: Business identifier
            doc_id: Document ID
            
        Returns:
            True if deleted
        """
        store = self._stores.get(business_id)
        if store:
            store.delete_document(doc_id)
        
        docs = self._business_documents.get(business_id, {})
        if doc_id in docs:
            del docs[doc_id]
            return True
        return False
    
    def clear_business(self, business_id: str) -> bool:
        """Clear all documents for a business.
        
        Args:
            business_id: Business identifier
            
        Returns:
            True if cleared
        """
        if business_id in self._stores:
            del self._stores[business_id]
        if business_id in self._business_documents:
            del self._business_documents[business_id]
        return True
    
    def get_statistics(self, business_id: str) -> Dict[str, Any]:
        """Get knowledge base statistics.
        
        Args:
            business_id: Business identifier
            
        Returns:
            Statistics dictionary
        """
        store = self._stores.get(business_id)
        docs = self._business_documents.get(business_id, {})
        
        doc_type_counts: Dict[str, int] = {}
        for doc in docs.values():
            doc_type_counts[doc.doc_type.value] = doc_type_counts.get(doc.doc_type.value, 0) + 1
        
        return {
            "total_documents": len(docs),
            "document_types": doc_type_counts,
            "business_id": business_id,
        }
