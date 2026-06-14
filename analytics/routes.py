"""Analytics routes."""

from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, render_template, send_file
from flask_login import login_required, current_user
from sqlalchemy import func, desc, and_
from app import db

from models.comment import Comment
from models.conversation import Conversation, Message
from models.lead import Lead
from models.resource import Resource
from models.instagram import InstagramAccount, EventLog
from models.ai_processing_log import AIProcessingLog

analytics_bp = Blueprint("analytics", __name__)


def get_date_range(period: str) -> tuple:
    """Get date range based on period."""
    end_date = datetime.utcnow()
    start_date = {
        'daily': end_date - timedelta(days=1),
        'weekly': end_date - timedelta(weeks=1),
        'monthly': end_date - timedelta(days=30),
        'quarterly': end_date - timedelta(days=90),
        'yearly': end_date - timedelta(days=365),
    }.get(period, end_date - timedelta(days=30))
    return start_date, end_date


def get_business_id():
    """Get business ID from current user."""
    if current_user.is_authenticated and hasattr(current_user, 'business_id'):
        return current_user.business_id
    return None


@analytics_bp.route("/")
def index():
    """Analytics home page."""
    return render_template("analytics/index.html")


@analytics_bp.route("/overview")
def overview():
    """Analytics overview page."""
    return render_template("analytics/overview.html")


@analytics_bp.route("/instagram")
def instagram():
    """Instagram analytics page."""
    return render_template("analytics/instagram.html")


@analytics_bp.route("/engagement")
def engagement():
    """Engagement analytics page."""
    return render_template("analytics/engagement.html")


@analytics_bp.route("/growth")
def growth():
    """Growth analytics page."""
    return render_template("analytics/growth.html")


@analytics_bp.route("/reports", methods=["GET", "POST"])
def reports():
    """Reports page."""
    return render_template("analytics/reports.html")


@analytics_bp.route("/api/overview", methods=["GET"])
def api_overview():
    """Analytics overview API - returns aggregated metrics."""
    period = request.args.get('period', 'monthly')
    start_date, end_date = get_date_range(period)
    business_id = get_business_id()
    
    # Get metrics from database
    metrics = get_analytics_metrics(business_id, start_date, end_date, period)
    
    return jsonify(metrics)


@analytics_bp.route("/api/instagram", methods=["GET"])
def api_instagram():
    """Instagram analytics API."""
    period = request.args.get('period', 'monthly')
    start_date, end_date = get_date_range(period)
    business_id = get_business_id()
    
    # Instagram-specific metrics
    ig_metrics = get_instagram_metrics(business_id, start_date, end_date)
    
    return jsonify(ig_metrics)


@analytics_bp.route("/api/engagement", methods=["GET"])
def api_engagement():
    """Engagement analytics API."""
    period = request.args.get('period', 'monthly')
    start_date, end_date = get_date_range(period)
    business_id = get_business_id()
    
    # Engagement metrics
    engagement = get_engagement_metrics(business_id, start_date, end_date)
    
    return jsonify(engagement)


@analytics_bp.route("/api/growth", methods=["GET"])
def api_growth():
    """Growth analytics API."""
    period = request.args.get('period', 'monthly')
    start_date, end_date = get_date_range(period)
    business_id = get_business_id()
    
    # Growth metrics
    growth = get_growth_metrics(business_id, start_date, end_date, period)
    
    return jsonify(growth)


@analytics_bp.route("/api/reports", methods=["GET", "POST"])
def api_reports():
    """Reports API - generate and retrieve reports."""
    if request.method == "POST":
        data = request.get_json() or {}
        report_type = data.get('type', 'weekly')
        period = data.get('period', 'monthly')
        
        # Generate report
        report = generate_report(report_type, period)
        return jsonify({
            'success': True,
            'report': report,
            'message': f'{report_type.title()} report generated successfully'
        })
    
    # GET - list reports
    reports = get_recent_reports()
    return jsonify({'reports': reports})


@analytics_bp.route("/api/reports/<report_id>", methods=["GET"])
def api_report_detail(report_id):
    """Report detail API."""
    report = get_report_by_id(report_id)
    if report:
        return jsonify(report)
    return jsonify({'error': 'Report not found'}), 404


@analytics_bp.route("/api/reports/email-config", methods=["GET"])
def api_email_config():
    """Get email report configuration status."""
    # Check if user has email configured
    email_configured = False
    if current_user.is_authenticated and current_user.email:
        email_configured = True
    
    return jsonify({
        'configured': email_configured,
        'email': current_user.email if email_configured else None
    })


@analytics_bp.route("/api/reports/email", methods=["POST"])
def api_email_report():
    """Email analytics report to configured address."""
    data = request.get_json() or {}
    report_type = data.get('type', 'weekly')
    period = data.get('period', 'monthly')
    recipient_email = data.get('email', None)
    
    # Use user's email if not specified
    if not recipient_email and current_user.is_authenticated:
        recipient_email = current_user.email
    
    if not recipient_email:
        return jsonify({
            'success': False,
            'error': 'No email address configured'
        }), 400
    
    # Queue email report (in production, this would use a task queue like Celery)
    email_sent = queue_email_report(report_type, period, recipient_email)
    
    return jsonify({
        'success': email_sent,
        'message': f'Report will be sent to {recipient_email}',
        'recipient': recipient_email
    })


@analytics_bp.route("/api/reports/schedule", methods=["POST"])
def api_schedule_report():
    """Schedule recurring report generation and delivery."""
    data = request.get_json() or {}
    
    frequency = data.get('frequency', 'weekly')  # daily, weekly, monthly
    report_type = data.get('type', 'analytics')
    delivery_email = data.get('email', current_user.email if current_user.is_authenticated else None)
    
    if not delivery_email:
        return jsonify({
            'success': False,
            'error': 'Email address required for scheduled reports'
        }), 400
    
    # Create scheduled report record
    report = schedule_recurring_report(frequency, report_type, delivery_email)
    
    return jsonify({
        'success': True,
        'report': report.to_dict() if report else None,
        'message': f'Report scheduled for {frequency} delivery'
    })


@analytics_bp.route("/api/export", methods=["POST"])
def api_export():
    """Export analytics API - CSV/JSON export."""
    data = request.get_json() or {}
    export_format = data.get('format', 'csv')
    period = data.get('period', 'monthly')
    start_date, end_date = get_date_range(period)
    business_id = get_business_id()
    
    # Get export data
    export_data = get_export_data(business_id, start_date, end_date, export_format)
    
    return jsonify({
        'success': True,
        'format': export_format,
        'data': export_data,
        'downloadUrl': f'/analytics/api/export/download?period={period}&format={export_format}'
    })


@analytics_bp.route("/api/export/download", methods=["GET"])
def api_export_download():
    """Download exported analytics data."""
    period = request.args.get('period', 'monthly')
    export_format = request.args.get('format', 'csv')
    start_date, end_date = get_date_range(period)
    business_id = get_business_id()
    
    # Generate export file
    export_data = get_export_data(business_id, start_date, end_date, export_format)
    
    if export_format == 'csv':
        import io
        import csv
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Metric', 'Value', 'Period'])
        
        # Data
        for key, value in export_data.items():
            writer.writerow([key, value, period])
        
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'analytics-export-{period}-{datetime.now().strftime("%Y%m%d")}.csv'
        )
    
    return jsonify(export_data)


# ============================================
# Analytics Helper Functions
# ============================================

def get_analytics_metrics(business_id, start_date, end_date, period):
    """Get comprehensive analytics metrics from database."""
    
    # Build base filters
    base_filters = []
    if business_id:
        base_filters.append(Comment.business_id == business_id)
    base_filters.append(Comment.created_at >= start_date)
    base_filters.append(Comment.created_at <= end_date)
    
    # Comments count
    comments_count = Comment.query.filter(*base_filters).count()
    
    # Conversations count
    conv_filters = []
    if business_id:
        conv_filters.append(Conversation.business_id == business_id)
    conv_filters.append(Conversation.created_at >= start_date)
    conv_filters.append(Conversation.created_at <= end_date)
    conversations_count = Conversation.query.filter(*conv_filters).count()
    
    # DM Volume (messages count)
    subquery = db.session.query(Conversation.id).filter(*conv_filters).subquery()
    dm_count = Message.query.filter(Message.conversation_id.in_(subquery)).count()
    
    # Leads count
    lead_filters = []
    if business_id:
        lead_filters.append(Lead.business_id == business_id)
    lead_filters.append(Lead.created_at >= start_date)
    lead_filters.append(Lead.created_at <= end_date)
    leads_count = Lead.query.filter(*lead_filters).count()
    
    # Lead growth percentage (compare to previous period)
    prev_start, prev_end = get_previous_period(start_date, end_date, period)
    prev_lead_filters = []
    if business_id:
        prev_lead_filters.append(Lead.business_id == business_id)
    prev_lead_filters.append(Lead.created_at >= prev_start)
    prev_lead_filters.append(Lead.created_at <= prev_end)
    prev_leads = Lead.query.filter(*prev_lead_filters).count()
    
    lead_growth = ((leads_count - prev_leads) / max(prev_leads, 1)) * 100 if prev_leads > 0 else 0
    
    # Resource usage
    res_filters = []
    if business_id:
        res_filters.append(Resource.business_id == business_id)
    res_filters.append(Resource.created_at >= start_date)
    res_filters.append(Resource.created_at <= end_date)
    resource_usage = Resource.query.filter(*res_filters).count()
    
    # Calculate trends (compare to previous period)
    trends = calculate_trends(business_id, start_date, end_date, prev_start, prev_end, period)
    
    # Get chart data
    chart_data = get_chart_data(business_id, start_date, end_date, period)
    
    # Get top questions (from AI processing logs)
    top_questions = get_top_questions(business_id, start_date, end_date)
    
    # Get top resources
    top_resources = get_top_resources(business_id, start_date, end_date)
    
    # Get intent distribution
    intent_distribution = get_intent_distribution(business_id, start_date, end_date)
    
    return {
        'comments': comments_count,
        'conversations': conversations_count,
        'dmVolume': dm_count,
        'leads': leads_count,
        'leadGrowth': round(lead_growth, 1),
        'resources': resource_usage,
        'trends': trends,
        'chartData': chart_data,
        'topQuestions': top_questions,
        'topResources': top_resources,
        'intentDistribution': intent_distribution,
        'period': period,
        'dateRange': {
            'start': start_date.isoformat(),
            'end': end_date.isoformat()
        }
    }


def get_instagram_metrics(business_id, start_date, end_date):
    """Get Instagram-specific analytics."""
    
    # Get connected Instagram accounts
    ig_filters = []
    if business_id:
        ig_filters.append(InstagramAccount.business_id == business_id)
    ig_filters.append(InstagramAccount.is_connected == True)
    
    accounts = InstagramAccount.query.filter(*ig_filters).all()
    account_ids = [acc.id for acc in accounts]
    
    if not account_ids:
        return {
            'totalAccounts': 0,
            'totalFollowers': 0,
            'totalComments': 0,
            'totalDMs': 0,
            'engagementRate': 0
        }
    
    # Comments from Instagram
    ig_comments = Comment.query.filter(
        Comment.instagram_account_id.in_(account_ids),
        Comment.created_at >= start_date,
        Comment.created_at <= end_date,
        Comment.is_deleted == False
    ).count()
    
    # Conversations from Instagram
    ig_conversations = Conversation.query.filter(
        Conversation.instagram_account_id.in_(account_ids),
        Conversation.created_at >= start_date,
        Conversation.created_at <= end_date
    ).count()
    
    # Total followers
    total_followers = sum(acc.followers_count or 0 for acc in accounts)
    
    # Engagement rate
    engagement_rate = 0
    if total_followers > 0:
        engagement_rate = ((ig_comments + ig_conversations) / total_followers) * 100
    
    return {
        'totalAccounts': len(accounts),
        'totalFollowers': total_followers,
        'totalComments': ig_comments,
        'totalDMs': ig_conversations,
        'engagementRate': round(engagement_rate, 2),
        'accounts': [{'username': acc.username, 'followers': acc.followers_count} for acc in accounts]
    }


def get_engagement_metrics(business_id, start_date, end_date):
    """Get engagement analytics."""
    
    # Average sentiment from comments
    avg_sentiment = db.session.query(func.avg(Comment.sentiment_score)).filter(
        Comment.business_id == business_id if business_id else True,
        Comment.created_at >= start_date,
        Comment.created_at <= end_date,
        Comment.sentiment_score.isnot(None)
    ).scalar() or 0
    
    # Auto-reply rate
    total_comments = Comment.query.filter(
        Comment.business_id == business_id if business_id else True,
        Comment.created_at >= start_date,
        Comment.created_at <= end_date
    ).count()
    
    auto_replies = Comment.query.filter(
        Comment.business_id == business_id if business_id else True,
        Comment.created_at >= start_date,
        Comment.created_at <= end_date,
        Comment.auto_reply_enabled == True
    ).count()
    
    auto_reply_rate = (auto_replies / total_comments * 100) if total_comments > 0 else 0
    
    return {
        'avgSentiment': round(avg_sentiment, 2),
        'autoReplyRate': round(auto_reply_rate, 1),
        'totalInteractions': total_comments,
        'sentimentTrend': get_sentiment_trend(business_id, start_date, end_date)
    }


def get_growth_metrics(business_id, start_date, end_date, period):
    """Get growth analytics."""
    
    # Leads by status
    lead_statuses = db.session.query(
        Lead.lead_status,
        func.count(Lead.id)
    ).filter(
        Lead.business_id == business_id if business_id else True,
        Lead.created_at >= start_date,
        Lead.created_at <= end_date
    ).group_by(Lead.lead_status).all()
    
    lead_status_dict = {status: count for status, count in lead_statuses}
    
    # Lead conversion rate
    converted_leads = Lead.query.filter(
        Lead.business_id == business_id if business_id else True,
        Lead.created_at >= start_date,
        Lead.created_at <= end_date,
        Lead.converted_at.isnot(None)
    ).count()
    
    total_leads = Lead.query.filter(
        Lead.business_id == business_id if business_id else True,
        Lead.created_at >= start_date,
        Lead.created_at <= end_date
    ).count()
    
    conversion_rate = (converted_leads / total_leads * 100) if total_leads > 0 else 0
    
    # Average lead score
    avg_lead_score = db.session.query(func.avg(Lead.lead_score)).filter(
        Lead.business_id == business_id if business_id else True,
        Lead.created_at >= start_date,
        Lead.created_at <= end_date
    ).scalar() or 0
    
    return {
        'leadByStatus': lead_status_dict,
        'totalLeads': total_leads,
        'convertedLeads': converted_leads,
        'conversionRate': round(conversion_rate, 1),
        'avgLeadScore': round(avg_lead_score, 1),
        'growthRate': calculate_lead_growth(business_id, start_date, end_date, period)
    }


def get_chart_data(business_id, start_date, end_date, period):
    """Get chart-ready data."""
    
    # Determine bucket size based on period
    bucket_count = 12  # Always return 12 data points
    
    if period == 'daily':
        delta = (end_date - start_date) / bucket_count
    elif period == 'weekly':
        delta = timedelta(weeks=1)
    elif period == 'quarterly':
        delta = timedelta(days=7)  # Weekly buckets
    elif period == 'yearly':
        delta = timedelta(weeks=4)  # Monthly buckets
    else:  # monthly
        delta = timedelta(days=2)  # Every 2 days
    
    labels = []
    comments_data = []
    conversations_data = []
    dms_data = []
    
    for i in range(bucket_count):
        bucket_start = start_date + (delta * i)
        bucket_end = bucket_start + delta
        
        labels.append(bucket_start.strftime('%b %d'))
        
        # Comments in this bucket
        comments = Comment.query.filter(
            Comment.business_id == business_id if business_id else True,
            Comment.created_at >= bucket_start,
            Comment.created_at < bucket_end
        ).count()
        comments_data.append(comments)
        
        # Conversations in this bucket
        conversations = Conversation.query.filter(
            Conversation.business_id == business_id if business_id else True,
            Conversation.created_at >= bucket_start,
            Conversation.created_at < bucket_end
        ).count()
        conversations_data.append(conversations)
        
        # DMs in this bucket
        conv_subquery = db.session.query(Conversation.id).filter(
            Conversation.business_id == business_id if business_id else True,
            Conversation.created_at >= bucket_start,
            Conversation.created_at < bucket_end
        ).subquery()
        dms = Message.query.filter(
            Message.conversation_id.in_(conv_subquery)
        ).count()
        dms_data.append(dms)
    
    return {
        'labels': labels,
        'comments': comments_data,
        'conversations': conversations_data,
        'dms': dms_data
    }


def get_top_questions(business_id, start_date, end_date):
    """Get top questions from AI processing logs."""
    
    # Query AI processing logs for common patterns
    top_questions = AIProcessingLog.query.filter(
        AIProcessingLog.business_id == business_id if business_id else True,
        AIProcessingLog.created_at >= start_date,
        AIProcessingLog.created_at <= end_date
    ).group_by(
        AIProcessingLog.intent,
        AIProcessingLog.comment_text
    ).order_by(
        desc(func.count(AIProcessingLog.id))
    ).limit(5).all()
    
    # Group by intent to identify top questions
    intent_counts = db.session.query(
        AIProcessingLog.intent,
        func.count(AIProcessingLog.id).label('count')
    ).filter(
        AIProcessingLog.business_id == business_id if business_id else True,
        AIProcessingLog.created_at >= start_date,
        AIProcessingLog.created_at <= end_date
    ).group_by(AIProcessingLog.intent).order_by(desc('count')).limit(5).all()
    
    return [
        {'text': intent, 'count': count}
        for intent, count in intent_counts
    ]


def get_top_resources(business_id, start_date, end_date):
    """Get top resources by view count."""
    
    resources = Resource.query.filter(
        Resource.business_id == business_id if business_id else True,
        Resource.created_at >= start_date,
        Resource.created_at <= end_date,
        Resource.is_published == True
    ).order_by(desc(Resource.view_count)).limit(5).all()
    
    return [
        {'title': r.title, 'views': r.view_count or 0, 'type': r.resource_type}
        for r in resources
    ]


def get_intent_distribution(business_id, start_date, end_date):
    """Get intent distribution from AI processing logs."""
    
    intent_counts = db.session.query(
        AIProcessingLog.intent,
        func.count(AIProcessingLog.id).label('count')
    ).filter(
        AIProcessingLog.business_id == business_id if business_id else True,
        AIProcessingLog.created_at >= start_date,
        AIProcessingLog.created_at <= end_date
    ).group_by(AIProcessingLog.intent).all()
    
    total = sum(count for _, count in intent_counts)
    
    return [
        {
            'name': intent.replace('_', ' ').title(),
            'value': round((count / total * 100) if total > 0 else 0),
            'count': count
        }
        for intent, count in intent_counts
    ]


def calculate_trends(business_id, current_start, current_end, prev_start, prev_end, period):
    """Calculate trend percentages compared to previous period."""
    
    trends = {}
    
    # Comments trend
    current_comments = Comment.query.filter(
        Comment.business_id == business_id if business_id else True,
        Comment.created_at >= current_start,
        Comment.created_at <= current_end
    ).count()
    
    prev_comments = Comment.query.filter(
        Comment.business_id == business_id if business_id else True,
        Comment.created_at >= prev_start,
        Comment.created_at <= prev_end
    ).count()
    
    trends['comments'] = calculate_percent_change(prev_comments, current_comments)
    
    # Conversations trend
    current_convs = Conversation.query.filter(
        Conversation.business_id == business_id if business_id else True,
        Conversation.created_at >= current_start,
        Conversation.created_at <= current_end
    ).count()
    
    prev_convs = Conversation.query.filter(
        Conversation.business_id == business_id if business_id else True,
        Conversation.created_at >= prev_start,
        Conversation.created_at <= prev_end
    ).count()
    
    trends['conversations'] = calculate_percent_change(prev_convs, current_convs)
    
    # DMs trend
    current_conv_ids = db.session.query(Conversation.id).filter(
        Conversation.business_id == business_id if business_id else True,
        Conversation.created_at >= current_start,
        Conversation.created_at <= current_end
    ).subquery()
    
    current_dms = Message.query.filter(
        Message.conversation_id.in_(current_conv_ids)
    ).count()
    
    prev_conv_ids = db.session.query(Conversation.id).filter(
        Conversation.business_id == business_id if business_id else True,
        Conversation.created_at >= prev_start,
        Conversation.created_at <= prev_end
    ).subquery()
    
    prev_dms = Message.query.filter(
        Message.conversation_id.in_(prev_conv_ids)
    ).count()
    
    trends['dmVolume'] = calculate_percent_change(prev_dms, current_dms)
    
    # Leads trend
    current_leads = Lead.query.filter(
        Lead.business_id == business_id if business_id else True,
        Lead.created_at >= current_start,
        Lead.created_at <= current_end
    ).count()
    
    prev_leads = Lead.query.filter(
        Lead.business_id == business_id if business_id else True,
        Lead.created_at >= prev_start,
        Lead.created_at <= prev_end
    ).count()
    
    trends['leads'] = calculate_percent_change(prev_leads, current_leads)
    trends['leadGrowth'] = trends['leads']  # Same as leads trend
    
    # Resources trend
    current_res = Resource.query.filter(
        Resource.business_id == business_id if business_id else True,
        Resource.created_at >= current_start,
        Resource.created_at <= current_end
    ).count()
    
    prev_res = Resource.query.filter(
        Resource.business_id == business_id if business_id else True,
        Resource.created_at >= prev_start,
        Resource.created_at <= prev_end
    ).count()
    
    trends['resources'] = calculate_percent_change(prev_res, current_res)
    
    return trends


def calculate_percent_change(old_value, new_value):
    """Calculate percentage change between two values."""
    if old_value == 0:
        return 100.0 if new_value > 0 else 0.0
    return round(((new_value - old_value) / old_value) * 100, 1)


def get_previous_period(start_date, end_date, period):
    """Get the previous period dates."""
    delta = end_date - start_date
    prev_end = start_date
    prev_start = prev_end - delta
    return prev_start, prev_end


def get_sentiment_trend(business_id, start_date, end_date):
    """Get sentiment trend over time."""
    # Simplified - in production, would aggregate over time buckets
    return {'trend': 'stable', 'change': 0}


def calculate_lead_growth(business_id, start_date, end_date, period):
    """Calculate lead growth rate."""
    prev_start, prev_end = get_previous_period(start_date, end_date, period)
    
    current_leads = Lead.query.filter(
        Lead.business_id == business_id if business_id else True,
        Lead.created_at >= start_date,
        Lead.created_at <= end_date
    ).count()
    
    prev_leads = Lead.query.filter(
        Lead.business_id == business_id if business_id else True,
        Lead.created_at >= prev_start,
        Lead.created_at <= prev_end
    ).count()
    
    return calculate_percent_change(prev_leads, current_leads)


def generate_report(report_type, period):
    """Generate an analytics report."""
    start_date, end_date = get_date_range(period)
    business_id = get_business_id()
    
    metrics = get_analytics_metrics(business_id, start_date, end_date, period)
    
    return {
        'id': f'report_{datetime.now().strftime("%Y%m%d%H%M%S")}',
        'type': report_type,
        'period': period,
        'generated_at': datetime.now().isoformat(),
        'metrics': metrics,
        'dateRange': {
            'start': start_date.isoformat(),
            'end': end_date.isoformat()
        }
    }


def get_recent_reports():
    """Get list of recent reports (in production, would query database)."""
    return []


def get_report_by_id(report_id):
    """Get a specific report by ID."""
    # In production, would query database
    return None


def get_export_data(business_id, start_date, end_date, export_format):
    """Get data formatted for export."""
    metrics = get_analytics_metrics(business_id, start_date, end_date, 'monthly')
    
    return {
        'comments': metrics.get('comments', 0),
        'conversations': metrics.get('conversations', 0),
        'dm_volume': metrics.get('dmVolume', 0),
        'leads': metrics.get('leads', 0),
        'lead_growth': metrics.get('leadGrowth', 0),
        'resource_usage': metrics.get('resources', 0),
        'period_start': start_date.isoformat(),
        'period_end': end_date.isoformat()
    }


def queue_email_report(report_type, period, recipient_email):
    """
    Queue an email report for delivery.
    
    In production, this would:
    1. Generate the report data
    2. Create PDF/HTML attachment
    3. Send via email service (SendGrid, AWS SES, etc.)
    4. Log the delivery status
    
    For now, returns True to indicate successful queue.
    """
    # Import here to avoid circular imports
    from flask import current_app
    
    try:
        # Generate report data
        start_date, end_date = get_date_range(period)
        business_id = get_business_id()
        metrics = get_analytics_metrics(business_id, start_date, end_date, period)
        
        # In production, would use Celery/Redis or similar for async processing:
        # email_report_task.delay(report_type, period, recipient_email, metrics)
        
        # For now, log the request
        current_app.logger.info(
            f"Email report queued: type={report_type}, period={period}, "
            f"recipient={recipient_email}, business_id={business_id}"
        )
        
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to queue email report: {str(e)}")
        return False


def schedule_recurring_report(frequency, report_type, delivery_email):
    """
    Create a scheduled recurring report.
    
    Args:
        frequency: 'daily', 'weekly', or 'monthly'
        report_type: Type of report to generate
        delivery_email: Email to send reports to
    
    Returns:
        Report model instance or None on failure
    """
    from models.report import Report
    from datetime import datetime, timedelta
    
    business_id = get_business_id()
    if not business_id:
        return None
    
    # Calculate next run time based on frequency
    now = datetime.utcnow()
    if frequency == 'daily':
        next_run = now + timedelta(days=1)
        date_range_start = now - timedelta(days=1)
        date_range_end = now
    elif frequency == 'weekly':
        next_run = now + timedelta(weeks=1)
        date_range_start = now - timedelta(weeks=1)
        date_range_end = now
    else:  # monthly
        next_run = now + timedelta(days=30)
        date_range_start = now - timedelta(days=30)
        date_range_end = now
    
    # Create scheduled report
    report = Report(
        business_id=business_id,
        user_id=current_user.id if current_user.is_authenticated else None,
        name=f"{report_type.title()} Report - {frequency}",
        description=f"Scheduled {frequency} {report_type} report",
        report_type=report_type,
        report_format='pdf',
        date_range_start=date_range_start,
        date_range_end=date_range_end,
        is_scheduled=True,
        schedule_frequency=frequency,
        next_run_at=next_run,
        status=Report.STATUS_PENDING,
        parameters={
            'delivery_email': delivery_email,
            'frequency': frequency
        }
    )
    
    try:
        db.session.add(report)
        db.session.commit()
        return report
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to create scheduled report: {str(e)}")
        return None


def get_scheduled_reports(business_id=None):
    """Get all scheduled reports for a business."""
    from models.report import Report
    
    query = Report.query.filter(Report.is_scheduled == True)
    
    if business_id:
        query = query.filter(Report.business_id == business_id)
    
    return query.order_by(Report.next_run_at).all()


def cancel_scheduled_report(report_id):
    """Cancel a scheduled report."""
    from models.report import Report
    
    report = Report.query.get(report_id)
    if report:
        report.is_scheduled = False
        report.status = Report.STATUS_CANCELLED if hasattr(Report, 'STATUS_CANCELLED') else 'cancelled'
        db.session.commit()
        return True
    return False