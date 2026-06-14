"""AI DM Employee API Routes - REST endpoints for AI DM operations."""

from flask import Blueprint, request, jsonify, current_app
from functools import wraps
import asyncio
from typing import Dict, Any

# Import AI DM Employee components
try:
    from services.ai_dm_employee import (
        AIDMEmployee,
        ConversationMemoryManager,
        BusinessContextManager,
        KnowledgeBaseService,
        SafetyValidator,
        ModerationLayer,
        HallucinationPrevention,
        AIDMLoggingService,
    )
    from services.ai_dm_employee.business_context import BusinessContext
except ImportError:
    AIDMEmployee = None
    ConversationMemoryManager = None

ai_dm_bp = Blueprint("ai_dm", __name__, url_prefix="/api/ai-dm")


# ============================================================================
# Global State (In production, use Redis or similar)
# ============================================================================

_employee_instances: Dict[str, AIDMEmployee] = {}
_conversation_memory = ConversationMemoryManager()
_business_context_manager = BusinessContextManager()
_knowledge_base = KnowledgeBaseService()


# ============================================================================
# Authentication Decorator
# ============================================================================

def require_auth(f):
    """Decorator to require authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Check for API key or session auth
        api_key = request.headers.get("X-API-Key")
        auth_header = request.headers.get("Authorization")
        
        if not api_key and not auth_header:
            return jsonify({"error": "Authentication required"}), 401
        
        return f(*args, **kwargs)
    return decorated


def require_business(f):
    """Decorator to require business context."""
    @wraps(f)
    def decorated(*args, **kwargs):
        business_id = request.headers.get("X-Business-ID") or request.json.get("business_id") if request.is_json else None
        
        if not business_id:
            return jsonify({"error": "Business ID required"}), 400
        
        # Check if employee instance exists
        if business_id not in _employee_instances:
            return jsonify({"error": "AI DM Employee not initialized for this business"}), 404
        
        return f(*args, **kwargs)
    return decorated


# ============================================================================
# Initialization Endpoints
# ============================================================================

@ai_dm_bp.route("/initialize", methods=["POST"])
@require_auth
def initialize_employee():
    """Initialize AI DM Employee for a business.
    
    Request Body:
    {
        "business_id": "string",
        "business_name": "string",
        "business_type": "string",
        "industry": "string",
        "description": "string",
        "website": "string",
        "email": "string",
        "phone": "string",
        "products": [],
        "services": [],
        "faq": [{"question": "...", "answer": "..."}],
        "ai_personality": "professional|friendly|casual",
        "ai_tone": "friendly|formal|casual",
        "ai_config": {...}
    }
    """
    if not request.is_json:
        return jsonify({"error": "JSON body required"}), 400
    
    data = request.json
    business_id = data.get("business_id")
    
    if not business_id:
        return jsonify({"error": "business_id is required"}), 400
    
    try:
        # Create business context
        business_context = BusinessContext(
            business_id=business_id,
            business_name=data.get("business_name", "Business"),
            business_type=data.get("business_type", ""),
            industry=data.get("industry", ""),
            description=data.get("description", ""),
            website=data.get("website", ""),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            products=data.get("products", []),
            services=data.get("services", []),
            faq=data.get("faq", []),
            ai_personality=data.get("ai_personality", "professional"),
            ai_tone=data.get("ai_tone", "friendly"),
        )
        
        # Get AI provider manager from app config or create default
        ai_provider_manager = current_app.config.get("AI_PROVIDER_MANAGER")
        
        if not ai_provider_manager:
            # Create a simple fallback manager
            from services.ai_dm_employee.employee import AIDMEmployee
            ai_provider_manager = None
        
        # Create AI DM Employee
        employee = AIDMEmployee(
            business_id=business_id,
            business_context=business_context,
            ai_provider_manager=ai_provider_manager,
            config=data.get("ai_config", {}),
        )
        
        _employee_instances[business_id] = employee
        
        # Also store in business context manager
        _business_context_manager.create_context_from_dict(
            business_id=business_id,
            data={
                "name": data.get("business_name", "Business"),
                "business_type": data.get("business_type", ""),
                "industry": data.get("industry", ""),
                "description": data.get("description", ""),
                "website": data.get("website", ""),
                "email": data.get("email", ""),
                "phone": data.get("phone", ""),
                "products": data.get("products", []),
                "services": data.get("services", []),
                "faq": data.get("faq", []),
                "ai_personality": data.get("ai_personality", "professional"),
                "ai_tone": data.get("ai_tone", "friendly"),
            }
        )
        
        # Index FAQ and products
        if data.get("faq"):
            _knowledge_base.index_faq(business_id, data["faq"])
        
        if data.get("products"):
            _knowledge_base.index_products(business_id, data["products"])
        
        return jsonify({
            "success": True,
            "message": "AI DM Employee initialized successfully",
            "business_id": business_id,
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to initialize: {str(e)}"
        }), 500


@ai_dm_bp.route("/initialize/<business_id>", methods=["GET"])
@require_auth
def get_initialization_status(business_id: str):
    """Get initialization status of AI DM Employee.
    
    Returns the current status and statistics.
    """
    if business_id not in _employee_instances:
        return jsonify({
            "initialized": False,
            "business_id": business_id,
        }), 200
    
    employee = _employee_instances[business_id]
    stats = employee.get_statistics()
    
    return jsonify({
        "initialized": True,
        "business_id": business_id,
        "status": stats.get("status", "unknown"),
        "statistics": stats,
    }), 200


@ai_dm_bp.route("/initialize/<business_id>", methods=["DELETE"])
@require_auth
def deinitialize_employee(business_id: str):
    """Deinitialize AI DM Employee for a business.
    
    Cleans up resources and removes the instance.
    """
    if business_id in _employee_instances:
        del _employee_instances[business_id]
    
    _knowledge_base.clear_business(business_id)
    _business_context_manager.remove_context(business_id)
    
    return jsonify({
        "success": True,
        "message": f"AI DM Employee deinitialized for business {business_id}",
    }), 200


# ============================================================================
# Message Processing Endpoints
# ============================================================================

@ai_dm_bp.route("/process", methods=["POST"])
@require_auth
def process_message():
    """Process an incoming message.
    
    Request Body:
    {
        "business_id": "string",
        "conversation_id": "string",
        "user_id": "string",
        "username": "string",
        "message": "string",
        "context": {...}  // optional
    }
    """
    if not request.is_json:
        return jsonify({"error": "JSON body required"}), 400
    
    data = request.json
    business_id = data.get("business_id")
    conversation_id = data.get("conversation_id")
    user_id = data.get("user_id")
    username = data.get("username", "user")
    message = data.get("message")
    
    # Validation
    if not all([business_id, conversation_id, user_id, message]):
        return jsonify({
            "error": "business_id, conversation_id, user_id, and message are required"
        }), 400
    
    # Check if employee is initialized
    if business_id not in _employee_instances:
        return jsonify({
            "error": "AI DM Employee not initialized. Call /api/ai-dm/initialize first."
        }), 404
    
    try:
        employee = _employee_instances[business_id]
        
        # Process message asynchronously
        if asyncio.iscoroutinefunction(employee.process_message):
            result = asyncio.run(employee.process_message(
                conversation_id=conversation_id,
                user_id=user_id,
                username=username,
                message=message,
                context=data.get("context"),
            ))
        else:
            # Fallback for sync processing
            result = employee.process_message(
                conversation_id=conversation_id,
                user_id=user_id,
                username=username,
                message=message,
                context=data.get("context"),
            )
        
        return jsonify({
            "success": result.success,
            "response": result.response,
            "confidence": result.confidence,
            "requires_human": result.requires_human,
            "should_send": result.should_send,
            "intent": result.intent,
            "entities": result.entities,
            "resources_recommended": result.resources_recommended,
            "follow_up_suggestions": result.follow_up_suggestions,
            "metadata": result.metadata,
            "processing_time_ms": result.processing_time_ms,
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to process message: {str(e)}"
        }), 500


@ai_dm_bp.route("/process/batch", methods=["POST"])
@require_auth
def process_batch_messages():
    """Process multiple messages.
    
    Request Body:
    {
        "business_id": "string",
        "messages": [
            {
                "conversation_id": "string",
                "user_id": "string",
                "username": "string",
                "message": "string"
            },
            ...
        ]
    }
    """
    if not request.is_json:
        return jsonify({"error": "JSON body required"}), 400
    
    data = request.json
    business_id = data.get("business_id")
    messages = data.get("messages", [])
    
    if not business_id or not messages:
        return jsonify({"error": "business_id and messages are required"}), 400
    
    if business_id not in _employee_instances:
        return jsonify({"error": "AI DM Employee not initialized"}), 404
    
    results = []
    for msg in messages:
        try:
            employee = _employee_instances[business_id]
            result = employee.process_message(
                conversation_id=msg.get("conversation_id"),
                user_id=msg.get("user_id"),
                username=msg.get("username", "user"),
                message=msg.get("message"),
                context=msg.get("context"),
            )
            results.append({
                "conversation_id": msg.get("conversation_id"),
                "success": result.success,
                "response": result.response,
            })
        except Exception as e:
            results.append({
                "conversation_id": msg.get("conversation_id"),
                "success": False,
                "error": str(e),
            })
    
    return jsonify({
        "results": results,
        "total": len(messages),
        "successful": sum(1 for r in results if r.get("success")),
    }), 200


# ============================================================================
# Conversation Management
# ============================================================================

@ai_dm_bp.route("/conversations/<conversation_id>/summary", methods=["GET"])
@require_auth
def get_conversation_summary(conversation_id: str):
    """Get summary of a conversation.
    
    Query Params:
    - business_id: Business identifier
    """
    business_id = request.args.get("business_id")
    
    if not business_id or business_id not in _employee_instances:
        return jsonify({"error": "Invalid business_id"}), 400
    
    try:
        employee = _employee_instances[business_id]
        summary = employee.get_conversation_summary(conversation_id)
        
        return jsonify({
            "conversation_id": conversation_id,
            "summary": summary,
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_dm_bp.route("/conversations/<conversation_id>/lead", methods=["GET"])
@require_auth
def get_lead_info(conversation_id: str):
    """Get lead information for a conversation.
    
    Query Params:
    - business_id: Business identifier
    """
    business_id = request.args.get("business_id")
    
    if not business_id or business_id not in _employee_instances:
        return jsonify({"error": "Invalid business_id"}), 400
    
    try:
        employee = _employee_instances[business_id]
        lead_info = employee.get_lead_info(conversation_id)
        
        return jsonify({
            "conversation_id": conversation_id,
            "lead": lead_info,
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_dm_bp.route("/conversations/<conversation_id>/clear", methods=["POST"])
@require_auth
def clear_conversation(conversation_id: str):
    """Clear conversation from memory.
    
    Query Params:
    - business_id: Business identifier
    """
    business_id = request.args.get("business_id")
    
    if not business_id or business_id not in _employee_instances:
        return jsonify({"error": "Invalid business_id"}), 400
    
    try:
        employee = _employee_instances[business_id]
        cleared = employee.clear_conversation(conversation_id)
        
        return jsonify({
            "success": cleared,
            "conversation_id": conversation_id,
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_dm_bp.route("/conversations/<conversation_id>/human-takeover", methods=["POST"])
@require_auth
def request_human_takeover(conversation_id: str):
    """Request human takeover for a conversation.
    
    Query Params:
    - business_id: Business identifier
    
    Request Body:
    {
        "reason": "string",
        "priority": "normal|high|urgent"
    }
    """
    business_id = request.args.get("business_id")
    
    if not business_id or business_id not in _employee_instances:
        return jsonify({"error": "Invalid business_id"}), 400
    
    try:
        employee = _employee_instances[business_id]
        
        # Update conversation memory
        employee.conversation_memory.request_human_takeover(
            conversation_id=conversation_id,
            reason=request.json.get("reason", "Manual request") if request.is_json else "Manual request",
        )
        
        return jsonify({
            "success": True,
            "conversation_id": conversation_id,
            "status": "escalated",
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_dm_bp.route("/conversations/<conversation_id>/human-takeover/release", methods=["POST"])
@require_auth
def release_human_takeover(conversation_id: str):
    """Release conversation from human takeover (AI can resume).
    
    Query Params:
    - business_id: Business identifier
    """
    business_id = request.args.get("business_id")
    
    if not business_id or business_id not in _employee_instances:
        return jsonify({"error": "Invalid business_id"}), 400
    
    try:
        employee = _employee_instances[business_id]
        employee.conversation_memory.clear_human_takeover(conversation_id)
        
        return jsonify({
            "success": True,
            "conversation_id": conversation_id,
            "status": "released",
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Knowledge Base Management
# ============================================================================

@ai_dm_bp.route("/knowledge/add", methods=["POST"])
@require_auth
def add_knowledge():
    """Add knowledge to the knowledge base.
    
    Request Body:
    {
        "business_id": "string",
        "type": "faq|product|service|text",
        "content": "string",
        "title": "string",  // optional
        "tags": [],  // optional
        "metadata": {}  // optional
    }
    """
    if not request.is_json:
        return jsonify({"error": "JSON body required"}), 400
    
    data = request.json
    business_id = data.get("business_id")
    
    if not business_id:
        return jsonify({"error": "business_id is required"}), 400
    
    try:
        from services.ai_dm_employee.knowledge_base import DocumentType
        
        doc_type_map = {
            "faq": DocumentType.FAQ,
            "product": DocumentType.PRODUCT,
            "service": DocumentType.SERVICE,
            "text": DocumentType.TEXT,
            "policy": DocumentType.POLICY,
            "manual": DocumentType.MANUAL,
        }
        
        doc_type = doc_type_map.get(data.get("type", "text"), DocumentType.TEXT)
        
        doc_id = _knowledge_base.index_document(
            business_id=business_id,
            content=data.get("content", ""),
            doc_type=doc_type,
            title=data.get("title", ""),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )
        
        return jsonify({
            "success": True,
            "document_id": doc_id,
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_dm_bp.route("/knowledge/search", methods=["GET"])
@require_auth
def search_knowledge():
    """Search the knowledge base.
    
    Query Params:
    - business_id: Business identifier
    - q: Search query
    - type: Optional document type filter
    - limit: Max results (default 10)
    """
    business_id = request.args.get("business_id")
    query = request.args.get("q", "")
    doc_type = request.args.get("type")
    limit = int(request.args.get("limit", 10))
    
    if not business_id or not query:
        return jsonify({"error": "business_id and q are required"}), 400
    
    try:
        from services.ai_dm_employee.knowledge_base import DocumentType
        
        doc_type_filter = None
        if doc_type:
            doc_type_filter = DocumentType(doc_type)
        
        results = _knowledge_base.search(
            business_id=business_id,
            query=query,
            top_k=limit,
            doc_type=doc_type_filter,
        )
        
        return jsonify({
            "results": [
                {
                    "id": r.document.id,
                    "content": r.document.content,
                    "title": r.document.title,
                    "score": r.score,
                    "highlights": r.highlights,
                }
                for r in results
            ],
            "total": len(results),
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_dm_bp.route("/knowledge/<document_id>", methods=["DELETE"])
@require_auth
def delete_knowledge(document_id: str):
    """Delete a document from the knowledge base.
    
    Query Params:
    - business_id: Business identifier
    """
    business_id = request.args.get("business_id")
    
    if not business_id:
        return jsonify({"error": "business_id is required"}), 400
    
    try:
        deleted = _knowledge_base.delete_document(business_id, document_id)
        
        return jsonify({
            "success": deleted,
            "document_id": document_id,
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Statistics and Monitoring
# ============================================================================

@ai_dm_bp.route("/statistics", methods=["GET"])
@require_auth
def get_statistics():
    """Get overall AI DM statistics.
    
    Query Params:
    - business_id: Business identifier (optional for global stats)
    """
    business_id = request.args.get("business_id")
    
    try:
        if business_id and business_id in _employee_instances:
            employee = _employee_instances[business_id]
            stats = employee.get_statistics()
        else:
            # Global statistics
            stats = {
                "total_businesses": len(_employee_instances),
                "businesses": list(_employee_instances.keys()),
            }
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@ai_dm_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "initialized_businesses": len(_employee_instances),
    }), 200


# ============================================================================
# Human Takeover Queue
# ============================================================================

@ai_dm_bp.route("/takeover/queue", methods=["GET"])
@require_auth
def get_takeover_queue():
    """Get all conversations pending human takeover.
    
    Query Params:
    - business_id: Business identifier
    """
    business_id = request.args.get("business_id")
    
    if not business_id or business_id not in _employee_instances:
        return jsonify({"error": "Invalid business_id"}), 400
    
    try:
        employee = _employee_instances[business_id]
        pending_ids = employee.conversation_memory.get_all_conversations_needing_human()
        
        pending = []
        for conv_id in pending_ids:
            context = employee.conversation_memory.get_context(conv_id)
            if context:
                pending.append({
                    "conversation_id": conv_id,
                    "participant_username": context.participant_username,
                    "reason": context.human_takeover_reason,
                    "created_at": context.created_at.isoformat(),
                })
        
        return jsonify({
            "queue": pending,
            "total": len(pending),
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Settings Management
# ============================================================================

@ai_dm_bp.route("/settings", methods=["GET", "PUT"])
@require_auth
def manage_settings():
    """Get or update AI DM settings.
    
    Query Params:
    - business_id: Business identifier
    
    Request Body (PUT):
    {
        "safety": {...},
        "moderation": {...},
        "hallucination_prevention": {...},
        "ai_config": {...}
    }
    """
    business_id = request.args.get("business_id")
    
    if not business_id or business_id not in _employee_instances:
        return jsonify({"error": "Invalid business_id"}), 400
    
    employee = _employee_instances[business_id]
    
    if request.method == "GET":
        return jsonify({
            "safety": {
                "blocked_topics": employee.safety_validator._blocked_topics,
                "offensive_words": employee.safety_validator.get_offensive_words(),
            },
            "moderation": {
                "level": employee.moderation_layer.level.value,
            },
            "hallucination_prevention": {
                "min_confidence": employee.hallucination_prevention.min_confidence_threshold,
                "strict_mode": employee.hallucination_prevention.strict_mode,
            },
        }), 200
    
    elif request.method == "PUT":
        if not request.is_json:
            return jsonify({"error": "JSON body required"}), 400
        
        data = request.json
        
        # Update safety settings
        if "safety" in data:
            if "blocked_topics" in data["safety"]:
                employee.safety_validator._blocked_topics = data["safety"]["blocked_topics"]
        
        # Update moderation settings
        if "moderation" in data:
            from services.ai_dm_employee.moderation import ModerationLevel
            if "level" in data["moderation"]:
                level = ModerationLevel(data["moderation"]["level"])
                employee.moderation_layer.set_level(level)
        
        # Update hallucination settings
        if "hallucination_prevention" in data:
            hp = data["hallucination_prevention"]
            employee.hallucination_prevention.configure(
                min_confidence=hp.get("min_confidence", 0.6),
                strict_mode=hp.get("strict_mode", False),
            )
        
        # Update AI config
        if "ai_config" in data:
            employee.config.update(data["ai_config"])
        
        return jsonify({"success": True}), 200
