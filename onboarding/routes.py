"""Onboarding routes for AI-first user onboarding flow."""
import os
import uuid
from flask import render_template, request, jsonify, session, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from onboarding import onboarding_bp

# Allowed file extensions for uploads
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "txt", "png", "jpg", "jpeg"}

# User type configurations
USER_TYPES = {
    "creator": {
        "name": "Creator",
        "icon": "sparkles",
        "description": "Influencers, artists, YouTubers, and content creators",
        "questions": [
            {"id": "niche", "question": "What's your content niche?", "placeholder": "e.g., Tech reviews, lifestyle, fitness...", "type": "text"},
            {"id": "platforms", "question": "What platforms do you create for?", "placeholder": "e.g., YouTube, Instagram, TikTok...", "type": "multi_select", "options": ["YouTube", "Instagram", "TikTok", "Twitter/X", "LinkedIn", "Podcast", "Blog"]},
            {"id": "monetization", "question": "How do you monetize?", "placeholder": "e.g., Sponsorships, merch, courses...", "type": "multi_select", "options": ["Sponsorships", "Ad Revenue", "Merchandise", "Courses", "Memberships", "Patreon", "Affiliate", "Consulting"]},
            {"id": "audience", "question": "What's your typical audience size?", "placeholder": "Select range...", "type": "select", "options": ["< 1K", "1K - 10K", "10K - 100K", "100K - 1M", "1M+"]},
        ]
    },
    "business": {
        "name": "Business",
        "icon": "briefcase",
        "description": "Companies, startups, and enterprises",
        "questions": [
            {"id": "industry", "question": "What industry are you in?", "placeholder": "e.g., SaaS, E-commerce, Finance...", "type": "text"},
            {"id": "company_size", "question": "What's your company size?", "placeholder": "Select size...", "type": "select", "options": ["1-10", "11-50", "51-200", "201-500", "500+"]},
            {"id": "target_audience", "question": "Who is your target audience?", "placeholder": "e.g., B2B, B2C, Enterprise...", "type": "multi_select", "options": ["B2B", "B2C", "Enterprise", "SMB", "Startup", "Individual Consumers"]},
            {"id": "goals", "question": "What are your main goals?", "placeholder": "Select goals...", "type": "multi_select", "options": ["Lead Generation", "Brand Awareness", "Customer Support", "Sales", "Recruitment"]},
        ]
    },
    "restaurant": {
        "name": "Restaurant",
        "icon": "utensils",
        "description": "Restaurants, cafes, bars, and food businesses",
        "questions": [
            {"id": "cuisine", "question": "What type of cuisine do you serve?", "placeholder": "e.g., Italian, Japanese, Mexican...", "type": "text"},
            {"id": "restaurant_type", "question": "What type of establishment?", "placeholder": "Select type...", "type": "select", "options": ["Fine Dining", "Casual Dining", "Fast Casual", "Fast Food", "Cafe", "Bar & Lounge", "Food Truck", "Bakeries"]},
            {"id": "services", "question": "What services do you offer?", "placeholder": "Select services...", "type": "multi_select", "options": ["Dine-in", "Takeout", "Delivery", "Catering", "Private Events"]},
            {"id": "price_range", "question": "What's your price range?", "placeholder": "Select range...", "type": "select", "options": ["$", "$$", "$$$", "$$$$"]},
        ]
    },
    "agency": {
        "name": "Agency",
        "icon": "users",
        "description": "Marketing, creative, and consulting agencies",
        "questions": [
            {"id": "agency_type", "question": "What type of agency?", "placeholder": "e.g., Marketing, Design, PR...", "type": "text"},
            {"id": "services", "question": "What services do you offer?", "placeholder": "Select services...", "type": "multi_select", "options": ["Digital Marketing", "Social Media", "SEO", "PPC", "Content Marketing", "Brand Strategy", "Web Design", "Video Production", "PR", "Consulting"]},
            {"id": "clients", "question": "What size clients do you work with?", "placeholder": "Select client size...", "type": "multi_select", "options": ["Startups", "SMB", "Enterprise", "Local Businesses", "International"]},
            {"id": "specialties", "question": "What are your specialties?", "placeholder": "e.g., E-commerce, Tech, Healthcare...", "type": "text"},
        ]
    },
    "coach": {
        "name": "Coach",
        "icon": "target",
        "description": "Life coaches, business coaches, and consultants",
        "questions": [
            {"id": "coaching_type", "question": "What type of coaching?", "placeholder": "e.g., Life, Business, Executive...", "type": "text"},
            {"id": "specialties", "question": "What are your specialties?", "placeholder": "e.g., Career, Relationships, Fitness...", "type": "multi_select", "options": ["Life Coaching", "Business Coaching", "Executive Coaching", "Career Coaching", "Health & Fitness", "Relationships", "Finance", "Leadership"]},
            {"id": "format", "question": "What format do you use?", "placeholder": "Select formats...", "type": "multi_select", "options": ["1-on-1 Sessions", "Group Coaching", "Workshops", "Online Courses", "Retreats", "Corporate Training"]},
            {"id": "experience", "question": "Years of experience?", "placeholder": "Select range...", "type": "select", "options": ["0-2 years", "3-5 years", "6-10 years", "10+ years"]},
        ]
    }
}


def allowed_file(filename):
    """Check if file extension is allowed."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@onboarding_bp.route("/")
def index():
    """Render the main onboarding page."""
    return render_template("onboarding/index.html", user_types=USER_TYPES)


@onboarding_bp.route("/welcome")
def welcome():
    """Render the welcome page."""
    return render_template("onboarding/welcome.html")


@onboarding_bp.route("/select-type")
def select_type():
    """Render the user type selection page."""
    return render_template("onboarding/select_type.html", user_types=USER_TYPES)


@onboarding_bp.route("/api/types")
def get_user_types():
    """Get all user types as JSON."""
    return jsonify(USER_TYPES)


@onboarding_bp.route("/api/type/<type_id>")
def get_user_type(type_id):
    """Get specific user type configuration."""
    if type_id not in USER_TYPES:
        return jsonify({"error": "User type not found"}), 404
    return jsonify(USER_TYPES[type_id])


@onboarding_bp.route("/conversation/<user_type>")
def conversation(user_type):
    """Render the AI conversation page for the selected user type."""
    if user_type not in USER_TYPES:
        return render_template("onboarding/error.html", message="Invalid user type"), 400
    
    user_config = USER_TYPES[user_type]
    return render_template(
        "onboarding/conversation.html", 
        user_type=user_type,
        user_config=user_config,
        all_questions=USER_TYPES
    )


@onboarding_bp.route("/api/conversation/respond", methods=["POST"])
def ai_response():
    """Generate AI response based on user input."""
    data = request.json
    user_input = data.get("message", "")
    user_type = data.get("user_type", "creator")
    context = data.get("context", {})
    
    # Generate contextual AI response
    response = generate_ai_response(user_input, user_type, context)
    
    return jsonify(response)


def generate_ai_response(message, user_type, context):
    """Generate contextual AI response based on user input and type."""
    message_lower = message.lower()
    
    # Smart response generation based on context and message
    if "website" in message_lower or "site" in message_lower:
        return {
            "message": "Perfect! Do you have a website you'd like to share? You can paste the URL here, or if you don't have one yet, I can help you set one up later.",
            "type": "input",
            "input_type": "url",
            "placeholder": "https://yourwebsite.com"
        }
    elif "instagram" in message_lower or "social" in message_lower:
        return {
            "message": "Great! What's your Instagram handle? This will help us showcase your social presence.",
            "type": "input",
            "input_type": "text",
            "placeholder": "@yourusername"
        }
    elif "pricing" in message_lower or "price" in message_lower or "cost" in message_lower:
        return {
            "message": "I'd love to know about your pricing structure. Do you have a pricing page or would you like to describe your pricing model?",
            "type": "input",
            "input_type": "textarea",
            "placeholder": "e.g., Starting at $99/month, or describe your pricing tiers..."
        }
    elif "portfolio" in message_lower or "work" in message_lower:
        return {
            "message": "Let's see your work! Do you have a portfolio URL or would you like to upload some samples?",
            "type": "input",
            "input_type": "text",
            "placeholder": "https://yourportfolio.com"
        }
    elif "github" in message_lower or "code" in message_lower:
        return {
            "message": "Awesome! Share your GitHub profile so I can see your technical work.",
            "type": "input",
            "input_type": "text",
            "placeholder": "username"
        }
    elif "youtube" in message_lower or "video" in message_lower:
        return {
            "message": "Let's check out your YouTube channel! What's your channel name or URL?",
            "type": "input",
            "input_type": "text",
            "placeholder": "Your Channel Name or @handle"
        }
    elif "faq" in message_lower:
        return {
            "message": "Let's create your FAQ section. Do you have common questions you'd like to add, or should I suggest some based on your profile?",
            "type": "suggestion",
            "suggestions": [
                "Add custom Q&A",
                "Suggest common questions",
                "Skip for now"
            ]
        }
    elif "resources" in message_lower or "links" in message_lower:
        return {
            "message": "Add helpful resources for your audience. This could be guides, tools, or external links.",
            "type": "input",
            "input_type": "textarea",
            "placeholder": "List your resources, one per line..."
        }
    elif "upload" in message_lower or "pdf" in message_lower or "brochure" in message_lower or "menu" in message_lower or "catalog" in message_lower:
        return {
            "message": "Upload your documents here. I can process PDFs, brochures, menus, or catalogs to extract information automatically.",
            "type": "upload",
            "accepted_types": [".pdf", ".doc", ".docx", ".png", ".jpg", ".jpeg"],
            "max_size": "10MB"
        }
    else:
        return {
            "message": "That's interesting! Tell me more about this, or I can move on to help with something else.",
            "type": "suggestion",
            "suggestions": [
                "Tell me more",
                "Add more details",
                "Move to next topic"
            ]
        }


@onboarding_bp.route("/upload", methods=["POST"])
def upload_file():
    """Handle file uploads during onboarding."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files["file"]
    upload_type = request.form.get("type", "general")
    
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    
    if file and allowed_file(file.filename):
        # Create unique filename
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        
        # Create upload folder if it doesn't exist
        upload_folder = os.path.join(current_app.root_path, "static", "uploads", "onboarding")
        os.makedirs(upload_folder, exist_ok=True)
        
        filepath = os.path.join(upload_folder, unique_filename)
        file.save(filepath)
        
        return jsonify({
            "success": True,
            "filename": unique_filename,
            "original_name": filename,
            "type": upload_type
        })
    
    return jsonify({"error": "File type not allowed"}), 400


@onboarding_bp.route("/profile")
def profile():
    """Render the profile creation page."""
    return render_template("onboarding/profile.html", user_types=USER_TYPES)


@onboarding_bp.route("/knowledge-base")
def knowledge_base():
    """Render the knowledge base creation page."""
    return render_template("onboarding/knowledge_base.html")


@onboarding_bp.route("/complete")
def complete():
    """Render the onboarding completion page."""
    return render_template("onboarding/complete.html")


@onboarding_bp.route("/api/save-profile", methods=["POST"])
def save_profile():
    """Save user profile data."""
    data = request.json
    
    # Store in session for now (in production, save to database)
    if "profile" not in session:
        session["profile"] = {}
    
    session["profile"].update(data)
    
    return jsonify({"success": True, "message": "Profile saved successfully"})


@onboarding_bp.route("/api/save-knowledge-base", methods=["POST"])
def save_knowledge_base():
    """Save knowledge base data."""
    data = request.json
    
    if "knowledge_base" not in session:
        session["knowledge_base"] = {}
    
    session["knowledge_base"].update(data)
    
    return jsonify({"success": True, "message": "Knowledge base saved successfully"})


@onboarding_bp.route("/api/complete-onboarding", methods=["POST"])
def complete_onboarding():
    """Mark onboarding as complete."""
    session["onboarding_complete"] = True
    
    return jsonify({
        "success": True, 
        "redirect": "/dashboard",
        "message": "Onboarding complete!"
    })


@onboarding_bp.route("/progress")
def get_progress():
    """Get onboarding progress status."""
    progress = {
        "step": session.get("onboarding_step", 0),
        "completed": session.get("onboarding_complete", False),
        "user_type": session.get("user_type", None)
    }
    return jsonify(progress)