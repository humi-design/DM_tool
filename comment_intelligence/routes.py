"""Comment Intelligence API routes."""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from services.ai_provider.service import AIService
from services.comment_intelligence import (
    CommentIntelligenceEngine,
    EngineConfig,
    CommentProcessor,
    IntentType,
)

comment_intelligence_bp = Blueprint("comment_intelligence", __name__, url_prefix="/api/comments/ai")

# Global engine instance
_engine = None
_processor = None


def get_engine() -> CommentIntelligenceEngine:
    """Get or create the Comment Intelligence Engine."""
    global _engine
    
    if _engine is None:
        # Try to initialize AI service
        ai_service = None
        try:
            if AIService.get_instance().is_initialized:
                ai_service = AIService.get_instance()
        except Exception:
            pass
        
        config = EngineConfig(
            ai_service=ai_service,
            enable_ai_fallback=True,
            enable_emoji_processing=True,
            enable_knowledge_retrieval=True,
        )
        _engine = CommentIntelligenceEngine(config)
    
    return _engine


def get_processor() -> CommentProcessor:
    """Get or create the Comment Processor."""
    global _processor
    
    if _processor is None:
        _processor = CommentProcessor(engine=get_engine())
    
    return _processor


@comment_intelligence_bp.route("/process", methods=["POST"])
@login_required
def process_comment():
    """Process a single comment through the intelligence pipeline.
    
    Request body:
    {
        "text": "Comment text to process",
        "author": "username" (optional),
        "is_reply": false (optional),
        "parent_comment": "..." (optional)
    }
    
    Returns:
    {
        "success": true,
        "data": {
            "comment_id": "...",
            "comment_text": "...",
            "intent": "interest|price|question|...",
            "intent_confidence": 0.85,
            "intent_reasoning": "...",
            "response": "Generated response",
            "should_reply": true,
            "actions": [...],
            "primary_action": "auto_reply",
            "has_emoji": false,
            "emoji_responses": [],
            "processing_time_ms": 150.5
        }
    }
    """
    data = request.get_json()
    
    if not data or "text" not in data:
        return jsonify({"success": False, "error": "Comment text is required"}), 400
    
    comment_text = data["text"]
    author = data.get("author")
    is_reply = data.get("is_reply", False)
    parent_comment = data.get("parent_comment")
    
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        processor = get_processor()
        result = loop.run_until_complete(
            processor.process_comment(
                text=comment_text,
                author_username=author,
                is_reply=is_reply,
                parent_comment=parent_comment,
            )
        )
        
        return jsonify({
            "success": True,
            "data": result.to_dict()
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        loop.close()


@comment_intelligence_bp.route("/process/batch", methods=["POST"])
@login_required
def process_batch():
    """Process multiple comments in batch.
    
    Request body:
    {
        "comments": [
            {"text": "...", "author": "..."},
            {"text": "...", "author": "..."}
        ]
    }
    
    Returns:
    {
        "success": true,
        "data": {
            "results": [...],
            "stats": {...}
        }
    }
    """
    data = request.get_json()
    
    if not data or "comments" not in data:
        return jsonify({"success": False, "error": "Comments list is required"}), 400
    
    comments = data["comments"]
    
    if len(comments) > 100:
        return jsonify({"success": False, "error": "Maximum 100 comments per batch"}), 400
    
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        processor = get_processor()
        results = loop.run_until_complete(processor.process_batch(comments))
        
        return jsonify({
            "success": True,
            "data": {
                "results": [r.to_dict() for r in results],
                "stats": processor.stats.to_dict()
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        loop.close()


@comment_intelligence_bp.route("/intent/detect", methods=["POST"])
@login_required
def detect_intent():
    """Detect intent for a comment.
    
    Request body:
    {
        "text": "Comment text"
    }
    
    Returns:
    {
        "success": true,
        "data": {
            "intent": "interest",
            "confidence": 0.85,
            "reasoning": "..."
        }
    }
    """
    data = request.get_json()
    
    if not data or "text" not in data:
        return jsonify({"success": False, "error": "Comment text is required"}), 400
    
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        engine = get_engine()
        result = loop.run_until_complete(engine.process(data["text"]))
        
        return jsonify({
            "success": True,
            "data": {
                "intent": result.intent.value if result.intent else "other",
                "confidence": result.intent_confidence,
                "reasoning": result.intent_reasoning,
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        loop.close()


@comment_intelligence_bp.route("/analytics", methods=["GET"])
@login_required
def get_analytics():
    """Get analytics from comment processing.
    
    Returns:
    {
        "success": true,
        "data": {
            "total_processed": 1000,
            "intent_distribution": {"interest": 300, "question": 200, ...},
            "average_confidence": 0.78,
            "average_processing_time_ms": 145.2,
            "error_rate": 0.02
        }
    }
    """
    engine = get_engine()
    
    analytics = engine.get_analytics()
    processor = get_processor()
    
    return jsonify({
        "success": True,
        "data": {
            "processing": analytics,
            "stats": processor.stats.to_dict(),
            "top_intents": processor.get_top_intents(),
        }
    })


@comment_intelligence_bp.route("/analytics/top-questions", methods=["GET"])
@login_required
def get_top_questions():
    """Get most common questions from comments.
    
    Returns:
    {
        "success": true,
        "data": [
            {"question": "How much does it cost?", "count": 15},
            ...
        ]
    }
    """
    processor = get_processor()
    questions = processor.get_most_common_questions()
    
    return jsonify({
        "success": True,
        "data": questions
    })


@comment_intelligence_bp.route("/analytics/intents", methods=["GET"])
@login_required
def get_intent_distribution():
    """Get intent distribution statistics.
    
    Returns:
    {
        "success": true,
        "data": {
            "distribution": {"interest": 30, "price": 20, ...},
            "total": 1000
        }
    }
    """
    processor = get_processor()
    stats = processor.stats.to_dict()
    
    return jsonify({
        "success": True,
        "data": {
            "distribution": stats.get("by_intent", {}),
            "total": stats.get("total_processed", 0)
        }
    })


@comment_intelligence_bp.route("/knowledge", methods=["GET"])
@login_required
def get_knowledge_entries():
    """Get all knowledge base entries.
    
    Returns:
    {
        "success": true,
        "data": {
            "entries": [...],
            "categories": ["resources", "support", ...],
            "count": 15
        }
    }
    """
    engine = get_engine()
    kb = engine.knowledge_base
    
    return jsonify({
        "success": True,
        "data": {
            "entries": kb.export_entries(),
            "categories": kb.categories,
            "count": kb.entry_count
        }
    })


@comment_intelligence_bp.route("/knowledge", methods=["POST"])
@login_required
def add_knowledge_entry():
    """Add a knowledge base entry.
    
    Request body:
    {
        "category": "resources",
        "title": "Menu Information",
        "content": "Our menu is available at...",
        "intent_types": ["resource", "question"],
        "keywords": ["menu", "items"],
        "priority": 8
    }
    
    Returns:
    {
        "success": true,
        "message": "Knowledge entry added"
    }
    """
    data = request.get_json()
    
    required_fields = ["category", "title", "content", "intent_types"]
    for field in required_fields:
        if field not in data:
            return jsonify({"success": False, "error": f"Field '{field}' is required"}), 400
    
    engine = get_engine()
    engine.add_knowledge_entry(
        category=data["category"],
        title=data["title"],
        content=data["content"],
        intent_types=data["intent_types"],
        keywords=data.get("keywords"),
        priority=data.get("priority", 5)
    )
    
    return jsonify({
        "success": True,
        "message": "Knowledge entry added successfully"
    })


@comment_intelligence_bp.route("/leads", methods=["GET"])
@login_required
def get_leads():
    """Get extracted leads from recent processing.
    
    Returns:
    {
        "success": true,
        "data": [
            {"username": "...", "intent": "interest", "comment_text": "...", ...},
            ...
        ]
    }
    """
    engine = get_engine()
    logs = engine.get_processing_logs(limit=500)
    
    leads = []
    lead_intents = {"interest", "price", "booking", "order"}
    
    for log in logs:
        intent = log.get("intent")
        if intent in lead_intents:
            leads.append({
                "username": log.get("author"),
                "intent": intent,
                "comment": log.get("comment"),
                "confidence": log.get("confidence"),
                "timestamp": log.get("timestamp"),
            })
    
    return jsonify({
        "success": True,
        "data": leads
    })


@comment_intelligence_bp.route("/logs", methods=["GET"])
@login_required
def get_processing_logs():
    """Get recent processing logs.
    
    Query params:
    - limit: Max number of logs (default 100)
    - intent: Filter by intent type
    
    Returns:
    {
        "success": true,
        "data": [...]
    }
    """
    limit = request.args.get("limit", 100, type=int)
    intent_filter = request.args.get("intent")
    
    engine = get_engine()
    logs = engine.get_processing_logs(limit=limit, intent_filter=intent_filter)
    
    return jsonify({
        "success": True,
        "data": logs
    })


@comment_intelligence_bp.route("/stats", methods=["GET"])
def get_stats():
    """Get processing statistics (public endpoint).
    
    Returns:
    {
        "success": true,
        "data": {
            "total_processed": 1000,
            "by_intent": {...},
            "average_confidence": 0.78,
            "average_processing_time_ms": 145.2
        }
    }
    """
    processor = get_processor()
    
    return jsonify({
        "success": True,
        "data": processor.stats.to_dict()
    })


@comment_intelligence_bp.route("/reset-stats", methods=["POST"])
@login_required
def reset_stats():
    """Reset processing statistics."""
    processor = get_processor()
    processor.reset_stats()
    
    return jsonify({
        "success": True,
        "message": "Statistics reset successfully"
    })


@comment_intelligence_bp.route("/intents", methods=["GET"])
def list_intents():
    """List all supported intent types.
    
    Returns:
    {
        "success": true,
        "data": {
            "intents": [
                {"value": "general", "label": "General", "description": "..."},
                ...
            ]
        }
    }
    """
    intents = [
        {"value": i.value, "label": i.value.title(), "description": _get_intent_description(i)}
        for i in IntentType
    ]
    
    return jsonify({
        "success": True,
        "data": {"intents": intents}
    })


@comment_intelligence_bp.route("/", methods=["GET"])
@login_required
def index():
    """Comment Intelligence dashboard page."""
    from flask import render_template
    return render_template("comment_intelligence/index.html")


def _get_intent_description(intent: IntentType) -> str:
    """Get description for an intent type."""
    descriptions = {
        IntentType.GENERAL: "General statements and casual remarks",
        IntentType.INTEREST: "Expressions of interest in products or services",
        IntentType.PRICE: "Questions about pricing and costs",
        IntentType.BOOKING: "Requests for appointments or reservations",
        IntentType.RESOURCE: "Requests for information, brochures, or files",
        IntentType.SUPPORT: "Help requests and support inquiries",
        IntentType.QUESTION: "Specific questions about features or details",
        IntentType.ORDER: "Requests to purchase or order",
        IntentType.GREETING: "Greetings and hellos",
        IntentType.OTHER: "Other types of comments",
    }
    return descriptions.get(intent, "")