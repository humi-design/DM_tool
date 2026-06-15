"""Leads routes."""

import csv
import io
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, render_template, Response

from app import db
from models.lead import Lead, LeadTimelineEvent
from models.business import Business
from flask_login import current_user, login_required
from functools import wraps
from utils.jwt import jwt_required, get_current_user_id

leads_bp = Blueprint("leads", __name__)


def get_current_business():
    """Get the current business for the user."""
    if hasattr(current_user, 'current_business_id') and current_user.current_business_id:
        return Business.query.get(current_user.current_business_id)
    business = Business.query.first()
    return business


def api_response(f):
    """Decorator for consistent API responses."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            result = f(*args, **kwargs)
            if isinstance(result, tuple):
                return jsonify(result[0]), result[1] if len(result) > 1 else 200
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e), "success": False}), 500
    return wrapper


# =============================================================================
# Page Routes
# =============================================================================

@leads_bp.route("/")
@login_required
def index():
    """Leads list page with dashboard."""
    return render_template("leads/index.html")


@leads_bp.route("/<lead_id>")
@login_required
def detail(lead_id):
    """Lead detail page."""
    return render_template("leads/detail.html", lead_id=lead_id)


@leads_bp.route("/pipeline")
@login_required
def pipeline():
    """Leads pipeline view."""
    return render_template("leads/pipeline.html")


@leads_bp.route("/funnel")
@login_required
def funnel():
    """Leads funnel view."""
    return render_template("leads/funnel.html")


@leads_bp.route("/segments", methods=["GET", "POST"])
@login_required
def segments():
    """Lead segments page."""
    return render_template("leads/segments.html")


# =============================================================================
# API Routes - CRUD Operations
# =============================================================================

@leads_bp.route("/api/leads", methods=["GET"])
@api_response
def api_list():
    """Get all leads with filtering, sorting, and pagination."""
    business = get_current_business()
    if not business:
        return {"success": False, "error": "No business found"}, 404
    
    # Query parameters
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    search = request.args.get("search", "")
    status = request.args.get("status", "")
    lead_status = request.args.get("lead_status", "")  # hot, warm, cold
    priority = request.args.get("priority", "")
    source = request.args.get("source", "")
    assigned_to = request.args.get("assigned_to", "")
    min_score = request.args.get("min_score", type=int)
    max_score = request.args.get("max_score", type=int)
    sort_by = request.args.get("sort_by", "created_at")
    sort_order = request.args.get("sort_order", "desc")
    
    # Build query
    query = Lead.query.filter_by(business_id=business.id, is_deleted=False)
    
    # Apply filters
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            db.or_(
                Lead.name.ilike(search_term),
                Lead.email.ilike(search_term),
                Lead.phone.ilike(search_term),
                Lead.company.ilike(search_term),
                Lead.instagram_username.ilike(search_term)
            )
        )
    
    if status:
        query = query.filter(Lead.status == status)
    
    if lead_status:
        query = query.filter(Lead.lead_status == lead_status)
    
    if priority:
        query = query.filter(Lead.priority == priority)
    
    if source:
        query = query.filter(Lead.source_type == source)
    
    if assigned_to:
        query = query.filter(Lead.assigned_to == assigned_to)
    
    if min_score is not None:
        query = query.filter(Lead.lead_score >= min_score)
    
    if max_score is not None:
        query = query.filter(Lead.lead_score <= max_score)
    
    # Sorting
    sort_column = getattr(Lead, sort_by, Lead.created_at)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    # Pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return {
        "success": True,
        "data": [lead.to_dict() for lead in pagination.items],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": pagination.total,
            "pages": pagination.pages,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev
        }
    }


@leads_bp.route("/api/leads", methods=["POST"])
@api_response
def api_create():
    """Create a new lead."""
    business = get_current_business()
    if not business:
        return {"success": False, "error": "No business found"}, 404
    
    data = request.get_json()
    if not data:
        return {"success": False, "error": "No data provided"}, 400
    
    lead = Lead(
        business_id=business.id,
        name=data.get("name"),
        email=data.get("email"),
        phone=data.get("phone"),
        company=data.get("company"),
        budget=data.get("budget"),
        interest=data.get("interest"),
        requirements=data.get("requirements"),
        source_type=data.get("source_type", "manual"),
        source_id=data.get("source_id"),
        source_name=data.get("source_name"),
        instagram_user_id=data.get("instagram_user_id"),
        instagram_username=data.get("instagram_username"),
        instagram_profile_url=data.get("instagram_profile_url"),
        lead_status=data.get("lead_status", "cold"),
        status=data.get("status", "new"),
        priority=data.get("priority", "normal"),
        lead_score=data.get("lead_score", 0),
        tags=data.get("tags", []),
        notes=data.get("notes"),
        assigned_to=data.get("assigned_to"),
        metadata_json=data.get("metadata", {})
    )
    
    db.session.add(lead)
    lead.add_timeline_event(LeadTimelineEvent.EVENT_CREATED, "Lead created")
    db.session.commit()
    
    return {"success": True, "data": lead.to_dict()}, 201


@leads_bp.route("/api/leads/<lead_id>", methods=["GET"])
@api_response
def api_detail(lead_id):
    """Get lead details."""
    lead = Lead.query.filter_by(id=lead_id, is_deleted=False).first()
    if not lead:
        return {"success": False, "error": "Lead not found"}, 404
    
    return {"success": True, "data": lead.to_dict()}


@leads_bp.route("/api/leads/<lead_id>", methods=["PUT"])
@api_response
def api_update(lead_id):
    """Update a lead."""
    lead = Lead.query.filter_by(id=lead_id, is_deleted=False).first()
    if not lead:
        return {"success": False, "error": "Lead not found"}, 404
    
    data = request.get_json()
    if not data:
        return {"success": False, "error": "No data provided"}, 400
    
    # Track changes for timeline
    changes = []
    
    # Update fields
    for field in ["name", "email", "phone", "company", "budget", "interest", 
                  "requirements", "source_name", "lead_status", "status", "priority",
                  "tags", "notes", "assigned_to"]:
        if field in data:
            old_val = getattr(lead, field)
            new_val = data[field]
            if old_val != new_val:
                setattr(lead, field, new_val)
                changes.append(f"{field}: {old_val} → {new_val}")
    
    # Update score if provided
    if "lead_score" in data:
        old_score = lead.lead_score
        lead.lead_score = data["lead_score"]
        if old_score != data["lead_score"]:
            changes.append(f"score: {old_score} → {data['lead_score']}")
    
    # Update metadata
    if "metadata" in data:
        lead.metadata_json = data["metadata"]
    
    db.session.commit()
    
    # Add timeline events for changes
    if changes:
        lead.add_timeline_event(
            LeadTimelineEvent.EVENT_UPDATED,
            f"Lead updated: {', '.join(changes)}"
        )
    
    return {"success": True, "data": lead.to_dict()}


@leads_bp.route("/api/leads/<lead_id>", methods=["DELETE"])
@api_response
def api_delete(lead_id):
    """Delete a lead (soft delete)."""
    lead = Lead.query.filter_by(id=lead_id, is_deleted=False).first()
    if not lead:
        return {"success": False, "error": "Lead not found"}, 404
    
    lead.soft_delete()
    lead.add_timeline_event(LeadTimelineEvent.EVENT_UPDATED, "Lead deleted")
    db.session.commit()
    
    return {"success": True, "message": "Lead deleted successfully"}


# =============================================================================
# Status & Pipeline Management
# =============================================================================

@leads_bp.route("/api/leads/<lead_id>/status", methods=["PUT"])
@api_response
def api_status(lead_id):
    """Update lead status (pipeline stage)."""
    lead = Lead.query.filter_by(id=lead_id, is_deleted=False).first()
    if not lead:
        return {"success": False, "error": "Lead not found"}, 404
    
    data = request.get_json()
    new_status = data.get("status")
    
    if not new_status:
        return {"success": False, "error": "Status is required"}, 400
    
    old_status = lead.status
    lead.status = new_status
    
    # Update funnel stage based on status
    status_to_funnel = {
        "new": "awareness",
        "contacted": "interest",
        "qualified": "consideration",
        "proposal": "intent",
        "won": "conversion",
        "lost": "lost"
    }
    lead.funnel_stage = status_to_funnel.get(new_status)
    
    db.session.commit()
    lead.add_timeline_event(
        LeadTimelineEvent.EVENT_STATUS_CHANGED,
        f"Status changed: {old_status} → {new_status}"
    )
    
    return {"success": True, "data": lead.to_dict()}


@leads_bp.route("/api/leads/<lead_id>/lead-status", methods=["PUT"])
@api_response
def api_lead_status(lead_id):
    """Update lead temperature status (hot/warm/cold)."""
    lead = Lead.query.filter_by(id=lead_id, is_deleted=False).first()
    if not lead:
        return {"success": False, "error": "Lead not found"}, 404
    
    data = request.get_json()
    new_status = data.get("lead_status")
    
    if new_status not in ["hot", "warm", "cold"]:
        return {"success": False, "error": "Invalid lead status"}, 400
    
    old_status = lead.lead_status
    lead.lead_status = new_status
    db.session.commit()
    
    lead.add_timeline_event(
        LeadTimelineEvent.EVENT_STATUS_CHANGED,
        f"Temperature changed: {old_status} → {new_status}"
    )
    
    return {"success": True, "data": lead.to_dict()}


@leads_bp.route("/api/leads/bulk-status", methods=["PUT"])
@api_response
def api_bulk_status():
    """Bulk update leads status."""
    data = request.get_json()
    lead_ids = data.get("lead_ids", [])
    new_status = data.get("status")
    
    if not lead_ids or not new_status:
        return {"success": False, "error": "Lead IDs and status are required"}, 400
    
    updated_count = Lead.query.filter(
        Lead.id.in_(lead_ids),
        Lead.is_deleted == False
    ).update({Lead.status: new_status}, synchronize_session=False)
    
    db.session.commit()
    
    return {"success": True, "updated": updated_count}


# =============================================================================
# Notes & Timeline
# =============================================================================

@leads_bp.route("/api/leads/<lead_id>/notes", methods=["GET"])
@api_response
def api_get_notes(lead_id):
    """Get lead notes."""
    lead = Lead.query.filter_by(id=lead_id, is_deleted=False).first()
    if not lead:
        return {"success": False, "error": "Lead not found"}, 404
    
    return {
        "success": True,
        "data": {
            "notes": lead.notes,
            "ai_generated_notes": lead.ai_generated_notes,
            "ai_summary": lead.ai_summary
        }
    }


@leads_bp.route("/api/leads/<lead_id>/notes", methods=["POST"])
@api_response
def api_add_note(lead_id):
    """Add a note to a lead."""
    lead = Lead.query.filter_by(id=lead_id, is_deleted=False).first()
    if not lead:
        return {"success": False, "error": "Lead not found"}, 404
    
    data = request.get_json()
    note = data.get("notes", "")
    
    if lead.notes:
        lead.notes = lead.notes + "\n\n" + note
    else:
        lead.notes = note
    
    db.session.commit()
    lead.add_timeline_event(
        LeadTimelineEvent.EVENT_NOTE_ADDED,
        f"Note added: {note[:100]}..." if len(note) > 100 else f"Note added: {note}"
    )
    
    return {"success": True, "data": lead.to_dict()}


@leads_bp.route("/api/leads/<lead_id>/timeline", methods=["GET"])
@api_response
def api_timeline(lead_id):
    """Get lead timeline events."""
    lead = Lead.query.filter_by(id=lead_id, is_deleted=False).first()
    if not lead:
        return {"success": False, "error": "Lead not found"}, 404
    
    events = LeadTimelineEvent.query.filter_by(lead_id=lead_id)\
        .order_by(LeadTimelineEvent.created_at.desc()).all()
    
    return {
        "success": True,
        "data": [event.to_dict() for event in events]
    }


@leads_bp.route("/api/leads/<lead_id>/timeline", methods=["POST"])
@api_response
def api_add_timeline_event(lead_id):
    """Add a timeline event to a lead."""
    lead = Lead.query.filter_by(id=lead_id, is_deleted=False).first()
    if not lead:
        return {"success": False, "error": "Lead not found"}, 404
    
    data = request.get_json()
    event_type = data.get("event_type")
    description = data.get("description")
    
    if not event_type or not description:
        return {"success": False, "error": "Event type and description are required"}, 400
    
    event = lead.add_timeline_event(event_type, description, data.get("metadata"))
    
    return {"success": True, "data": event.to_dict()}, 201


# =============================================================================
# Tags
# =============================================================================

@leads_bp.route("/api/leads/<lead_id>/tags", methods=["PUT"])
@api_response
def api_tags(lead_id):
    """Update lead tags."""
    lead = Lead.query.filter_by(id=lead_id, is_deleted=False).first()
    if not lead:
        return {"success": False, "error": "Lead not found"}, 404
    
    data = request.get_json()
    tags = data.get("tags", [])
    
    lead.tags = tags
    db.session.commit()
    
    return {"success": True, "data": lead.to_dict()}


# =============================================================================
# Pipeline View
# =============================================================================

@leads_bp.route("/api/pipeline", methods=["GET"])
@api_response
def api_pipeline():
    """Get leads grouped by pipeline status."""
    business = get_current_business()
    if not business:
        return {"success": False, "error": "No business found"}, 404
    
    stages = ["new", "contacted", "qualified", "proposal", "won", "lost"]
    pipeline_data = {}
    
    for stage in stages:
        leads = Lead.query.filter_by(
            business_id=business.id,
            status=stage,
            is_deleted=False
        ).order_by(Lead.lead_score.desc()).all()
        
        pipeline_data[stage] = {
            "count": len(leads),
            "leads": [lead.to_dict() for lead in leads]
        }
    
    return {"success": True, "data": pipeline_data}


# =============================================================================
# AI Features
# =============================================================================

@leads_bp.route("/api/leads/<lead_id>/score", methods=["POST"])
@api_response
def api_score_lead(lead_id):
    """Calculate AI score for a lead."""
    lead = Lead.query.filter_by(id=lead_id, is_deleted=False).first()
    if not lead:
        return {"success": False, "error": "Lead not found"}, 404
    
    from services.lead_intelligence import get_lead_intelligence_service
    
    service = get_lead_intelligence_service()
    lead_dict = lead.to_dict()
    
    result = service.calculate_score(lead_dict)
    
    # Update lead with new score
    lead.lead_score = result.score
    lead.ai_confidence = result.confidence
    lead.lead_status = service.categorize_lead(result.score)
    db.session.commit()
    
    lead.add_timeline_event(
        LeadTimelineEvent.EVENT_SCORE_CHANGED,
        f"AI scoring updated: {result.score}/100 ({lead.lead_status})"
    )
    
    return {
        "success": True,
        "data": {
            "score": result.score,
            "confidence": result.confidence,
            "lead_status": lead.lead_status,
            "factors": result.factors,
            "reasons": result.reasons,
            "recommendations": result.recommendations
        }
    }


@leads_bp.route("/api/leads/<lead_id>/analyze", methods=["POST"])
@api_response
def api_analyze_lead(lead_id):
    """Generate AI analysis for a lead."""
    lead = Lead.query.filter_by(id=lead_id, is_deleted=False).first()
    if not lead:
        return {"success": False, "error": "Lead not found"}, 404
    
    from services.lead_intelligence import get_lead_intelligence_service
    import asyncio
    
    service = get_lead_intelligence_service()
    lead_dict = lead.to_dict()
    
    # Run async analysis
    async def run_analysis():
        summary = await service.generate_summary(lead_dict)
        notes = await service.generate_notes(lead_dict)
        return summary, notes
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        summary, notes = loop.run_until_complete(run_analysis())
    finally:
        loop.close()
    
    # Update lead with AI insights
    lead.ai_summary = summary.summary
    lead.ai_generated_notes = notes
    
    # Also update score
    score_result = service.calculate_score(lead_dict)
    lead.lead_score = score_result.score
    lead.ai_confidence = score_result.confidence
    lead.lead_status = service.categorize_lead(score_result.score)
    
    db.session.commit()
    
    lead.add_timeline_event(
        LeadTimelineEvent.EVENT_AI_SUMMARY,
        "AI analysis generated"
    )
    
    return {
        "success": True,
        "data": {
            "summary": summary.summary,
            "key_points": summary.key_points,
            "intent_signals": summary.intent_signals,
            "concerns": summary.concerns,
            "next_steps": summary.next_steps,
            "ai_notes": notes,
            "score": score_result.score,
            "lead_status": lead.lead_status
        }
    }


@leads_bp.route("/api/leads/score-all", methods=["POST"])
@api_response
def api_score_all_leads():
    """Score all leads using AI."""
    business = get_current_business()
    if not business:
        return {"success": False, "error": "No business found"}, 404
    
    from services.lead_intelligence import get_lead_intelligence_service
    
    service = get_lead_intelligence_service()
    
    leads = Lead.query.filter_by(
        business_id=business.id,
        is_deleted=False
    ).all()
    
    scored = 0
    for lead in leads:
        lead_dict = lead.to_dict()
        result = service.calculate_score(lead_dict)
        
        lead.lead_score = result.score
        lead.ai_confidence = result.confidence
        lead.lead_status = service.categorize_lead(result.score)
        scored += 1
    
    db.session.commit()
    
    return {
        "success": True,
        "scored": scored,
        "message": f"Scored {scored} leads"
    }


@leads_bp.route("/api/leads/<lead_id>/conversion-probability", methods=["GET"])
@api_response
def api_conversion_probability(lead_id):
    """Get conversion probability for a lead."""
    lead = Lead.query.filter_by(id=lead_id, is_deleted=False).first()
    if not lead:
        return {"success": False, "error": "Lead not found"}, 404
    
    from services.lead_intelligence import get_lead_intelligence_service
    
    service = get_lead_intelligence_service()
    lead_dict = lead.to_dict()
    
    probability = service.predict_conversion_probability(lead_dict)
    score_result = service.calculate_score(lead_dict)
    
    return {
        "success": True,
        "data": {
            "probability": round(probability * 100, 1),
            "score": score_result.score,
            "recommendations": score_result.recommendations
        }
    }


@leads_bp.route("/api/leads/<lead_id>/sentiment", methods=["GET"])
@api_response
def api_sentiment(lead_id):
    """Analyze conversation sentiment for a lead."""
    lead = Lead.query.filter_by(id=lead_id, is_deleted=False).first()
    if not lead:
        return {"success": False, "error": "Lead not found"}, 404
    
    from services.lead_intelligence import get_lead_intelligence_service
    
    service = get_lead_intelligence_service()
    
    # Get conversation history (placeholder - would integrate with actual conversations)
    conversation_history = lead.metadata_json.get("conversation_history", [])
    
    sentiment = service.analyze_conversation_sentiment(conversation_history)
    
    return {
        "success": True,
        "data": sentiment
    }


@leads_bp.route("/api/pipeline/move", methods=["POST"])
@api_response
def api_pipeline_move():
    """Move a lead to a different pipeline stage."""
    data = request.get_json()
    lead_id = data.get("lead_id")
    new_status = data.get("status")
    
    lead = Lead.query.filter_by(id=lead_id, is_deleted=False).first()
    if not lead:
        return {"success": False, "error": "Lead not found"}, 404
    
    old_status = lead.status
    lead.status = new_status
    
    # Handle conversion
    if new_status == "won":
        lead.converted_at = datetime.utcnow()
        lead.add_timeline_event(LeadTimelineEvent.EVENT_CONVERTED, "Lead marked as won")
    
    db.session.commit()
    lead.add_timeline_event(
        LeadTimelineEvent.EVENT_STATUS_CHANGED,
        f"Moved from {old_status} to {new_status}"
    )
    
    return {"success": True, "data": lead.to_dict()}


# =============================================================================
# Statistics & Analytics
# =============================================================================

@leads_bp.route("/api/stats", methods=["GET"])
@api_response
def api_stats():
    """Get lead statistics."""
    business = get_current_business()
    if not business:
        return {"success": False, "error": "No business found"}, 404
    
    now = datetime.utcnow()
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)
    
    # Total leads
    total_leads = Lead.query.filter_by(
        business_id=business.id,
        is_deleted=False
    ).count()
    
    # Leads by temperature
    hot_leads = Lead.query.filter_by(
        business_id=business.id,
        lead_status="hot",
        is_deleted=False
    ).count()
    
    warm_leads = Lead.query.filter_by(
        business_id=business.id,
        lead_status="warm",
        is_deleted=False
    ).count()
    
    cold_leads = Lead.query.filter_by(
        business_id=business.id,
        lead_status="cold",
        is_deleted=False
    ).count()
    
    # Pipeline stats
    pipeline_stats = {}
    for stage in ["new", "contacted", "qualified", "proposal", "won", "lost"]:
        pipeline_stats[stage] = Lead.query.filter_by(
            business_id=business.id,
            status=stage,
            is_deleted=False
        ).count()
    
    # Conversion stats
    converted_leads = Lead.query.filter_by(
        business_id=business.id,
        status="won",
        is_deleted=False
    ).count()
    
    conversion_rate = (converted_leads / total_leads * 100) if total_leads > 0 else 0
    
    # Recent leads (last 7 days)
    recent_leads = Lead.query.filter(
        Lead.business_id == business.id,
        Lead.created_at >= seven_days_ago,
        Lead.is_deleted == False
    ).count()
    
    # Recent leads (last 30 days)
    leads_this_month = Lead.query.filter(
        Lead.business_id == business.id,
        Lead.created_at >= thirty_days_ago,
        Lead.is_deleted == False
    ).count()
    
    # Average score
    avg_score = db.session.query(db.func.avg(Lead.lead_score)).filter(
        Lead.business_id == business.id,
        Lead.is_deleted == False
    ).scalar() or 0
    
    # Top sources
    source_stats = db.session.query(
        Lead.source_type,
        db.func.count(Lead.id).label("count")
    ).filter(
        Lead.business_id == business.id,
        Lead.is_deleted == False
    ).group_by(Lead.source_type).all()
    
    sources = [{"source": s[0], "count": s[1]} for s in source_stats]
    
    return {
        "success": True,
        "data": {
            "total_leads": total_leads,
            "hot_leads": hot_leads,
            "warm_leads": warm_leads,
            "cold_leads": cold_leads,
            "pipeline": pipeline_stats,
            "converted_leads": converted_leads,
            "conversion_rate": round(conversion_rate, 2),
            "recent_leads": recent_leads,
            "leads_this_month": leads_this_month,
            "average_score": round(avg_score, 1),
            "sources": sources
        }
    }


@leads_bp.route("/api/stats/funnel", methods=["GET"])
@api_response
def api_funnel():
    """Get conversion funnel data."""
    business = get_current_business()
    if not business:
        return {"success": False, "error": "No business found"}, 404
    
    stages = ["new", "contacted", "qualified", "proposal", "won"]
    funnel_data = []
    
    for i, stage in enumerate(stages):
        count = Lead.query.filter_by(
            business_id=business.id,
            status=stage,
            is_deleted=False
        ).count()
        
        # Calculate drop-off rate
        if i > 0:
            prev_count = funnel_data[i - 1]["count"] if funnel_data else count
            drop_off = ((prev_count - count) / prev_count * 100) if prev_count > 0 else 0
        else:
            drop_off = 0
        
        funnel_data.append({
            "stage": stage,
            "count": count,
            "drop_off": round(drop_off, 1)
        })
    
    return {"success": True, "data": funnel_data}


@leads_bp.route("/api/stats/growth", methods=["GET"])
@api_response
def api_growth():
    """Get lead growth data for charts."""
    business = get_current_business()
    if not business:
        return {"success": False, "error": "No business found"}, 404
    
    days = request.args.get("days", 30, type=int)
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)
    
    # Get leads created per day
    daily_leads = db.session.query(
        db.func.date(Lead.created_at).label("date"),
        db.func.count(Lead.id).label("count")
    ).filter(
        Lead.business_id == business.id,
        Lead.created_at >= start_date,
        Lead.is_deleted == False
    ).group_by(db.func.date(Lead.created_at)).all()
    
    # Convert to format for charts
    growth_data = [{"date": str(d[0]), "count": d[1]} for d in daily_leads]
    
    return {"success": True, "data": growth_data}


# =============================================================================
# Export/Import
# =============================================================================

@leads_bp.route("/api/export", methods=["POST"])
def api_export():
    """Export leads to CSV."""
    business = get_current_business()
    if not business:
        return jsonify({"error": "No business found"}), 404
    
    data = request.get_json() or {}
    lead_ids = data.get("lead_ids")
    
    if lead_ids:
        leads = Lead.query.filter(
            Lead.id.in_(lead_ids),
            Lead.business_id == business.id,
            Lead.is_deleted == False
        ).all()
    else:
        leads = Lead.query.filter_by(
            business_id=business.id,
            is_deleted=False
        ).all()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "Name", "Email", "Phone", "Company", "Budget", "Interest",
        "Requirements", "Status", "Lead Status", "Score", "Priority",
        "Source", "Instagram", "Notes", "Tags", "Created At"
    ])
    
    # Data
    for lead in leads:
        writer.writerow([
            lead.name or "",
            lead.email or "",
            lead.phone or "",
            lead.company or "",
            lead.budget or "",
            lead.interest or "",
            lead.requirements or "",
            lead.status or "",
            lead.lead_status or "",
            lead.lead_score or 0,
            lead.priority or "",
            lead.source_type or "",
            lead.instagram_username or "",
            lead.notes or "",
            ",".join(lead.tags) if lead.tags else "",
            lead.created_at.strftime("%Y-%m-%d %H:%M:%S") if lead.created_at else ""
        ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=leads_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )


@leads_bp.route("/api/import", methods=["POST"])
@api_response
def api_import():
    """Import leads from CSV."""
    business = get_current_business()
    if not business:
        return {"success": False, "error": "No business found"}, 404
    
    if "file" not in request.files:
        return {"success": False, "error": "No file provided"}, 400
    
    file = request.files["file"]
    if not file.filename.endswith(".csv"):
        return {"success": False, "error": "File must be CSV"}, 400
    
    stream = io.StringIO(file.stream.read().decode("UTF-8"))
    reader = csv.DictReader(stream)
    
    imported = 0
    errors = []
    
    for row_num, row in enumerate(reader, start=2):
        try:
            lead = Lead(
                business_id=business.id,
                name=row.get("Name"),
                email=row.get("Email"),
                phone=row.get("Phone"),
                company=row.get("Company"),
                budget=row.get("Budget"),
                interest=row.get("Interest"),
                requirements=row.get("Requirements"),
                status=row.get("Status", "new"),
                lead_status=row.get("Lead Status", "cold"),
                priority=row.get("Priority", "normal"),
                source_type=row.get("Source", "import"),
                instagram_username=row.get("Instagram"),
                notes=row.get("Notes"),
                tags=row.get("Tags", "").split(",") if row.get("Tags") else []
            )
            
            try:
                lead.lead_score = int(row.get("Score", 0))
            except (ValueError, TypeError):
                lead.lead_score = 0
            
            db.session.add(lead)
            imported += 1
        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")
    
    db.session.commit()
    
    return {
        "success": True,
        "imported": imported,
        "errors": errors if errors else None
    }


# =============================================================================
# Segments
# =============================================================================

@leads_bp.route("/api/segments", methods=["GET"])
@api_response
def api_segments():
    """Get lead segments."""
    business = get_current_business()
    if not business:
        return {"success": False, "error": "No business found"}, 404
    
    # Pre-defined segments
    segments = [
        {
            "id": "hot_leads",
            "name": "Hot Leads",
            "description": "High-priority leads ready for immediate action",
            "filter": {"lead_status": "hot"}
        },
        {
            "id": "cold_outreach",
            "name": "Cold Outreach Needed",
            "description": "Cold leads that haven't been contacted",
            "filter": {"lead_status": "cold", "status": "new"}
        },
        {
            "id": "follow_up",
            "name": "Needs Follow-up",
            "description": "Leads not contacted in the last 7 days",
            "filter": {"status": "contacted"}
        },
        {
            "id": "high_value",
            "name": "High Value",
            "description": "Leads with score >= 70",
            "filter": {"min_score": 70}
        },
        {
            "id": "qualified",
            "name": "Qualified Leads",
            "description": "Leads in qualified pipeline stage",
            "filter": {"status": "qualified"}
        },
        {
            "id": "proposal_stage",
            "name": "Proposal Stage",
            "description": "Leads in proposal pipeline stage",
            "filter": {"status": "proposal"}
        }
    ]
    
    # Add counts to segments
    for segment in segments:
        query = Lead.query.filter_by(
            business_id=business.id,
            is_deleted=False
        )
        
        f = segment["filter"]
        if "lead_status" in f:
            query = query.filter(Lead.lead_status == f["lead_status"])
        if "status" in f:
            query = query.filter(Lead.status == f["status"])
        if "min_score" in f:
            query = query.filter(Lead.lead_score >= f["min_score"])
        
        segment["count"] = query.count()
    
    return {"success": True, "data": segments}


@leads_bp.route("/api/segments/<segment_id>", methods=["GET"])
@api_response
def api_segment_leads(segment_id):
    """Get leads for a specific segment."""
    business = get_current_business()
    if not business:
        return {"success": False, "error": "No business found"}, 404
    
    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=7)
    
    query = Lead.query.filter_by(
        business_id=business.id,
        is_deleted=False
    )
    
    if segment_id == "hot_leads":
        query = query.filter(Lead.lead_status == "hot")
    elif segment_id == "cold_outreach":
        query = query.filter(Lead.lead_status == "cold", Lead.status == "new")
    elif segment_id == "follow_up":
        query = query.filter(
            Lead.status == "contacted",
            db.or_(
                Lead.last_contacted_at < seven_days_ago,
                Lead.last_contacted_at.is_(None)
            )
        )
    elif segment_id == "high_value":
        query = query.filter(Lead.lead_score >= 70)
    elif segment_id == "qualified":
        query = query.filter(Lead.status == "qualified")
    elif segment_id == "proposal_stage":
        query = query.filter(Lead.status == "proposal")
    
    leads = query.order_by(Lead.lead_score.desc()).all()
    
    return {"success": True, "data": [lead.to_dict() for lead in leads]}


# =============================================================================
# Bulk Operations
# =============================================================================

@leads_bp.route("/api/leads/bulk/delete", methods=["POST"])
@api_response
def api_bulk_delete():
    """Bulk delete leads."""
    data = request.get_json()
    lead_ids = data.get("lead_ids", [])
    
    if not lead_ids:
        return {"success": False, "error": "No lead IDs provided"}, 400
    
    deleted_count = Lead.query.filter(
        Lead.id.in_(lead_ids),
        Lead.is_deleted == False
    ).update({Lead.is_deleted: True, Lead.deleted_at: datetime.utcnow()}, synchronize_session=False)
    
    db.session.commit()
    
    return {"success": True, "deleted": deleted_count}


@leads_bp.route("/api/leads/bulk/assign", methods=["POST"])
@api_response
def api_bulk_assign():
    """Bulk assign leads to a user."""
    data = request.get_json()
    lead_ids = data.get("lead_ids", [])
    user_id = data.get("assigned_to")
    
    if not lead_ids or not user_id:
        return {"success": False, "error": "Lead IDs and user ID are required"}, 400
    
    updated_count = Lead.query.filter(
        Lead.id.in_(lead_ids),
        Lead.is_deleted == False
    ).update({Lead.assigned_to: user_id}, synchronize_session=False)
    
    db.session.commit()
    
    return {"success": True, "updated": updated_count}