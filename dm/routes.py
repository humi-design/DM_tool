"""DM routes with AI DM Employee integration."""

from flask import Blueprint, request, jsonify, render_template, current_app
from functools import wraps
import asyncio
from datetime import datetime


dm_bp = Blueprint("dm", __name__)


# ============================================================================
# Authentication Decorator
# ============================================================================

def require_auth(f):
    """Decorator to require authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")
        auth_header = request.headers.get("Authorization")
        
        if not api_key and not auth_header:
            return jsonify({"error": "Authentication required"}), 401
        
        return f(*args, **kwargs)
    return decorated


# ============================================================================
# Page Routes
# ============================================================================

@dm_bp.route("/")
def index():
    """DM inbox page."""
    return render_template("dm/index.html")


@dm_bp.route("/threads")
def threads():
    """DM threads list page."""
    return render_template("dm/threads.html")


@dm_bp.route("/threads/<thread_id>")
def thread_detail(thread_id):
    """DM thread detail page."""
    return render_template("dm/thread_detail.html", thread_id=thread_id)


@dm_bp.route("/compose", methods=["GET", "POST"])
def compose():
    """Compose new DM page."""
    return render_template("dm/compose.html")


@dm_bp.route("/templates", methods=["GET", "POST"])
def templates():
    """DM templates page."""
    return render_template("dm/templates.html")


@dm_bp.route("/auto-reply", methods=["GET", "POST"])
def auto_reply():
    """Auto reply configuration page."""
    return render_template("dm/auto_reply.html")


# ============================================================================
# Thread/Conversation Management
# ============================================================================

@dm_bp.route("/api/threads", methods=["GET"])
@require_auth
def api_threads():
    """DM threads API.
    
    Query Params:
    - instagram_account_id: Filter by Instagram account
    - status: Filter by lead status
    - page: Page number
    - per_page: Items per page
    """
    # Get query parameters
    instagram_account_id = request.args.get("instagram_account_id")
    status = request.args.get("status")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    
    # Import models
    from app import db
    from models.conversation import Conversation
    
    # Build query
    query = Conversation.query.filter_by(is_deleted=False)
    
    if instagram_account_id:
        query = query.filter_by(instagram_account_id=instagram_account_id)
    
    if status:
        query = query.filter_by(lead_status=status)
    
    # Order by last message time
    query = query.order_by(Conversation.last_message_at.desc())
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        "threads": [t.to_dict() for t in pagination.items],
        "total": pagination.total,
        "page": page,
        "per_page": per_page,
        "pages": pagination.pages,
    })


@dm_bp.route("/api/threads/<thread_id>", methods=["GET", "PUT"])
@require_auth
def api_thread_detail(thread_id):
    """DM thread detail API."""
    from app import db
    from models.conversation import Conversation
    
    conversation = Conversation.query.filter_by(id=thread_id).first()
    
    if not conversation:
        return jsonify({"error": "Thread not found"}), 404
    
    if request.method == "GET":
        return jsonify(conversation.to_dict())
    
    elif request.method == "PUT":
        data = request.json or {}
        
        # Update fields
        if "lead_status" in data:
            conversation.lead_status = data["lead_status"]
        if "lead_priority" in data:
            conversation.lead_priority = data["lead_priority"]
        if "lead_notes" in data:
            conversation.lead_notes = data["lead_notes"]
        if "lead_tags" in data:
            conversation.lead_tags = data["lead_tags"]
        if "is_archived" in data:
            conversation.is_archived = data["is_archived"]
        if "is_muted" in data:
            conversation.is_muted = data["is_muted"]
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "thread": conversation.to_dict(),
        })


@dm_bp.route("/api/threads/<thread_id>/messages", methods=["GET"])
@require_auth
def api_messages(thread_id):
    """DM messages API.
    
    Query Params:
    - page: Page number
    - per_page: Items per page
    """
    from app import db
    from models.conversation import Conversation, Message
    
    conversation = Conversation.query.filter_by(id=thread_id).first()
    
    if not conversation:
        return jsonify({"error": "Thread not found"}), 404
    
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    
    query = Message.query.filter_by(
        conversation_id=thread_id,
        is_deleted=False
    ).order_by(Message.timestamp.desc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        "messages": [m.to_dict() for m in pagination.items],
        "total": pagination.total,
        "page": page,
        "per_page": per_page,
        "pages": pagination.pages,
    })


@dm_bp.route("/api/threads/<thread_id>/send", methods=["POST"])
@require_auth
def api_send(thread_id):
    """Send DM API."""
    from app import db
    from models.conversation import Conversation
    from services.instagram_service import InstagramService
    
    if not request.is_json:
        return jsonify({"error": "JSON body required"}), 400
    
    data = request.json
    message = data.get("message")
    media_url = data.get("media_url")
    
    if not message:
        return jsonify({"error": "Message is required"}), 400
    
    conversation = Conversation.query.filter_by(id=thread_id).first()
    
    if not conversation:
        return jsonify({"error": "Thread not found"}), 404
    
    try:
        # Get Instagram service
        instagram_service = InstagramService()
        
        # Send message via Instagram API
        result = instagram_service.send_direct_message(
            instagram_account_id=conversation.instagram_account_id,
            thread_id=conversation.thread_id,
            message=message,
            media_url=media_url,
        )
        
        if result.get("success"):
            # Update conversation
            conversation.last_message_text = message
            conversation.last_message_at = datetime.utcnow()
            conversation.messages_count += 1
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message_id": result.get("message_id"),
            })
        else:
            return jsonify({
                "error": result.get("error", "Failed to send message"),
            }), 500
            
    except Exception as e:
        return jsonify({
            "error": f"Failed to send message: {str(e)}",
        }), 500


@dm_bp.route("/api/compose", methods=["POST"])
@require_auth
def api_compose():
    """Compose and send DM API."""
    from services.instagram_service import InstagramService
    
    if not request.is_json:
        return jsonify({"error": "JSON body required"}), 400
    
    data = request.json
    instagram_account_id = data.get("instagram_account_id")
    recipient_id = data.get("recipient_id")
    recipient_username = data.get("recipient_username")
    message = data.get("message")
    media_url = data.get("media_url")
    
    if not all([instagram_account_id, recipient_id, message]):
        return jsonify({
            "error": "instagram_account_id, recipient_id, and message are required"
        }), 400
    
    try:
        instagram_service = InstagramService()
        
        result = instagram_service.send_direct_message(
            instagram_account_id=instagram_account_id,
            recipient_id=recipient_id,
            recipient_username=recipient_username,
            message=message,
            media_url=media_url,
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to send message: {str(e)}",
        }), 500


# ============================================================================
# Templates
# ============================================================================

@dm_bp.route("/api/templates", methods=["GET", "POST"])
@require_auth
def api_templates():
    """DM templates API."""
    from app import db
    from models.resource import Resource
    
    if request.method == "GET":
        templates = Resource.query.filter_by(
            resource_type="dm_template",
            is_deleted=False,
        ).order_by(Resource.created_at.desc()).all()
        
        return jsonify({
            "templates": [t.to_dict() for t in templates],
        })
    
    elif request.method == "POST":
        if not request.is_json:
            return jsonify({"error": "JSON body required"}), 400
        
        data = request.json
        
        template = Resource(
            business_id=data.get("business_id"),
            title=data.get("title", ""),
            content=data.get("content", ""),
            resource_type="dm_template",
            category=data.get("category", "general"),
            is_published=True,
        )
        
        db.session.add(template)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "template": template.to_dict(),
        }), 201


@dm_bp.route("/api/templates/<template_id>", methods=["GET", "PUT", "DELETE"])
@require_auth
def api_template_detail(template_id):
    """DM template detail API."""
    from app import db
    from models.resource import Resource
    
    template = Resource.query.filter_by(
        id=template_id,
        resource_type="dm_template",
    ).first()
    
    if not template:
        return jsonify({"error": "Template not found"}), 404
    
    if request.method == "GET":
        return jsonify(template.to_dict())
    
    elif request.method == "PUT":
        data = request.json or {}
        
        if "title" in data:
            template.title = data["title"]
        if "content" in data:
            template.content = data["content"]
        if "category" in data:
            template.category = data["category"]
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "template": template.to_dict(),
        })
    
    elif request.method == "DELETE":
        template.is_deleted = True
        db.session.commit()
        
        return jsonify({"success": True})


# ============================================================================
# Auto-Reply Configuration
# ============================================================================

@dm_bp.route("/api/auto-reply", methods=["GET", "POST", "PUT"])
@require_auth
def api_auto_reply():
    """Auto reply configuration API."""
    from app import db
    from models.setting import Setting
    
    if request.method == "GET":
        instagram_account_id = request.args.get("instagram_account_id")
        
        settings = Setting.query.filter_by(
            key=f"auto_reply_{instagram_account_id}" if instagram_account_id else "auto_reply_default",
        ).first()
        
        return jsonify({
            "settings": settings.to_dict() if settings else None,
        })
    
    elif request.method in ("POST", "PUT"):
        if not request.is_json:
            return jsonify({"error": "JSON body required"}), 400
        
        data = request.json
        instagram_account_id = data.get("instagram_account_id")
        
        setting = Setting.query.filter_by(
            key=f"auto_reply_{instagram_account_id}" if instagram_account_id else "auto_reply_default",
        ).first()
        
        if not setting:
            setting = Setting(
                key=f"auto_reply_{instagram_account_id}" if instagram_account_id else "auto_reply_default",
                value={},
            )
            db.session.add(setting)
        
        setting.value = {
            "enabled": data.get("enabled", True),
            "use_ai": data.get("use_ai", True),
            "template": data.get("template", ""),
            "keywords": data.get("keywords", []),
            "business_hours_only": data.get("business_hours_only", False),
            "ai_config": data.get("ai_config", {}),
        }
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "settings": setting.to_dict(),
        })


# ============================================================================
# Thread Actions
# ============================================================================

@dm_bp.route("/api/mark-read/<thread_id>", methods=["POST"])
@require_auth
def api_mark_read(thread_id):
    """Mark thread as read API."""
    from app import db
    from models.conversation import Conversation, Message
    
    conversation = Conversation.query.filter_by(id=thread_id).first()
    
    if not conversation:
        return jsonify({"error": "Thread not found"}), 404
    
    # Mark all unread messages as read
    Message.query.filter_by(
        conversation_id=thread_id,
        is_read=False,
        is_from_me=False,
    ).update({"is_read": True, "read_at": datetime.utcnow()})
    
    conversation.unread_count = 0
    db.session.commit()
    
    return jsonify({"success": True})


@dm_bp.route("/api/archive/<thread_id>", methods=["POST"])
@require_auth
def api_archive(thread_id):
    """Archive thread API."""
    from app import db
    from models.conversation import Conversation
    
    conversation = Conversation.query.filter_by(id=thread_id).first()
    
    if not conversation:
        return jsonify({"error": "Thread not found"}), 404
    
    conversation.is_archived = True
    db.session.commit()
    
    return jsonify({"success": True})


@dm_bp.route("/api/spam/<thread_id>", methods=["POST"])
@require_auth
def api_spam(thread_id):
    """Mark thread as spam API."""
    from app import db
    from models.conversation import Conversation
    
    conversation = Conversation.query.filter_by(id=thread_id).first()
    
    if not conversation:
        return jsonify({"error": "Thread not found"}), 404
    
    conversation.is_spam = True
    db.session.commit()
    
    return jsonify({"success": True})


# ============================================================================
# AI DM Employee Integration
# ============================================================================

@dm_bp.route("/api/ai/process", methods=["POST"])
@require_auth
def api_ai_process():
    """Process message with AI DM Employee.
    
    This endpoint integrates with the AI DM Employee service to provide
    intelligent auto-replies to direct messages.
    
    Request Body:
    {
        "business_id": "string",
        "instagram_account_id": "string",
        "conversation_id": "string",
        "user_id": "string",
        "username": "string",
        "message": "string"
    }
    """
    if not request.is_json:
        return jsonify({"error": "JSON body required"}), 400
    
    data = request.json
    
    # Validate required fields
    required = ["business_id", "conversation_id", "user_id", "username", "message"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400
    
    try:
        # Get or create AI DM Employee instance
        business_id = data["business_id"]
        employee = current_app.config.get("AI_DM_EMPLOYEES", {}).get(business_id)
        
        if not employee:
            return jsonify({
                "error": "AI DM Employee not initialized for this business",
                "hint": "Call /api/ai-dm/initialize first",
            }), 404
        
        # Process the message
        result = asyncio.run(employee.process_message(
            conversation_id=data["conversation_id"],
            user_id=data["user_id"],
            username=data["username"],
            message=data["message"],
            context={
                "instagram_account_id": data.get("instagram_account_id"),
            },
        ))
        
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
            "processing_time_ms": result.processing_time_ms,
        })
        
    except Exception as e:
        return jsonify({
            "error": f"AI processing failed: {str(e)}",
        }), 500


@dm_bp.route("/api/ai/auto-reply", methods=["POST"])
@require_auth
def api_ai_auto_reply():
    """AI auto-reply endpoint for incoming messages.
    
    This is the main integration point for Instagram webhook processing.
    
    Request Body:
    {
        "business_id": "string",
        "instagram_account_id": "string",
        "thread_id": "string",
        "sender_id": "string",
        "sender_username": "string",
        "message": "string",
        "message_type": "text|image|video"
    }
    """
    if not request.is_json:
        return jsonify({"error": "JSON body required"}), 400
    
    data = request.json
    
    required = ["business_id", "thread_id", "sender_id", "sender_username", "message"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400
    
    try:
        business_id = data["business_id"]
        instagram_account_id = data.get("instagram_account_id")
        thread_id = data["thread_id"]
        
        # Get AI DM Employee
        employees = current_app.config.get("AI_DM_EMPLOYEES", {})
        employee = employees.get(business_id)
        
        if not employee:
            return jsonify({
                "error": "AI DM Employee not initialized",
                "requires_setup": True,
            }), 404
        
        # Check if auto-reply is enabled for this account
        from models.setting import Setting
        setting = Setting.query.filter_by(
            key=f"auto_reply_{instagram_account_id}" if instagram_account_id else "auto_reply_default",
        ).first()
        
        if not setting or not setting.value.get("enabled", False):
            return jsonify({
                "skipped": True,
                "reason": "Auto-reply disabled",
            })
        
        # Check business hours if configured
        if setting.value.get("business_hours_only", False):
            if not _is_business_hours():
                return jsonify({
                    "skipped": True,
                    "reason": "Outside business hours",
                })
        
        # Process the message
        result = asyncio.run(employee.process_message(
            conversation_id=thread_id,
            user_id=data["sender_id"],
            username=data["sender_username"],
            message=data["message"],
            context={
                "instagram_account_id": instagram_account_id,
                "message_type": data.get("message_type", "text"),
            },
        ))
        
        # If response should be sent, save to database and return
        if result.should_send and result.success:
            # Save message to database
            from app import db
            from models.conversation import Conversation, Message
            
            # Find or create conversation
            conversation = Conversation.query.filter_by(
                instagram_account_id=instagram_account_id,
                thread_id=thread_id,
            ).first()
            
            if not conversation:
                conversation = Conversation(
                    instagram_account_id=instagram_account_id,
                    thread_id=thread_id,
                    participant_instagram_id=data["sender_id"],
                    participant_username=data["sender_username"],
                    lead_status="new",
                )
                db.session.add(conversation)
                db.session.flush()
            
            # Save user message
            user_msg = Message(
                conversation_id=conversation.id,
                instagram_message_id=data.get("instagram_message_id", f"ext_{datetime.utcnow().timestamp()}"),
                message_type=data.get("message_type", "text"),
                text=data["message"],
                sender_instagram_id=data["sender_id"],
                sender_username=data["sender_username"],
                is_from_me=False,
                is_read=True,
                timestamp=datetime.utcnow(),
            )
            db.session.add(user_msg)
            
            # Save AI response
            ai_msg = Message(
                conversation_id=conversation.id,
                instagram_message_id=f"ai_{datetime.utcnow().timestamp()}",
                message_type="text",
                text=result.response,
                sender_instagram_id="ai_assistant",
                is_from_me=True,
                is_read=True,
                is_auto_replied=True,
                auto_reply_trigger=result.intent,
                timestamp=datetime.utcnow(),
            )
            db.session.add(ai_msg)
            
            # Update conversation
            conversation.last_message_text = result.response
            conversation.last_message_at = datetime.utcnow()
            conversation.messages_count += 2
            
            db.session.commit()
            
            return jsonify({
                "success": True,
                "response": result.response,
                "conversation_id": conversation.id,
                "message_id": ai_msg.instagram_message_id,
                "confidence": result.confidence,
                "intent": result.intent,
                "requires_human": result.requires_human,
            })
        else:
            return jsonify({
                "success": False,
                "requires_human": result.requires_human,
                "reason": "Response not suitable for auto-reply",
            })
        
    except Exception as e:
        return jsonify({
            "error": f"Auto-reply processing failed: {str(e)}",
        }), 500


def _is_business_hours() -> bool:
    """Check if current time is within business hours.
    
    This is a simplified implementation. In production, you'd check
    against actual business hours stored in settings.
    """
    from datetime import time
    now = datetime.utcnow()
    current_time = now.time()
    
    # Simple check: 9 AM to 6 PM UTC
    return time(9, 0) <= current_time <= time(18, 0)


@dm_bp.route("/api/ai/human-takeover", methods=["POST"])
@require_auth
def api_ai_human_takeover():
    """Transfer conversation to human agent.
    
    Request Body:
    {
        "business_id": "string",
        "conversation_id": "string",
        "reason": "string"
    }
    """
    if not request.is_json:
        return jsonify({"error": "JSON body required"}), 400
    
    data = request.json
    
    business_id = data.get("business_id")
    conversation_id = data.get("conversation_id")
    
    if not all([business_id, conversation_id]):
        return jsonify({"error": "business_id and conversation_id are required"}), 400
    
    try:
        employees = current_app.config.get("AI_DM_EMPLOYEES", {})
        employee = employees.get(business_id)
        
        if not employee:
            return jsonify({"error": "AI DM Employee not found"}), 404
        
        # Request human takeover
        employee.conversation_memory.request_human_takeover(
            conversation_id=conversation_id,
            reason=data.get("reason", "Manual escalation"),
        )
        
        return jsonify({
            "success": True,
            "conversation_id": conversation_id,
            "status": "escalated",
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@dm_bp.route("/api/ai/conversation/<conversation_id>", methods=["GET"])
@require_auth
def api_ai_conversation_summary(conversation_id: str):
    """Get AI conversation summary and lead info.
    
    Query Params:
    - business_id: Business identifier
    """
    business_id = request.args.get("business_id")
    
    if not business_id:
        return jsonify({"error": "business_id is required"}), 400
    
    try:
        employees = current_app.config.get("AI_DM_EMPLOYEES", {})
        employee = employees.get(business_id)
        
        if not employee:
            return jsonify({"error": "AI DM Employee not found"}), 404
        
        summary = employee.get_conversation_summary(conversation_id)
        lead_info = employee.get_lead_info(conversation_id)
        
        return jsonify({
            "conversation_id": conversation_id,
            "summary": summary,
            "lead": lead_info,
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500