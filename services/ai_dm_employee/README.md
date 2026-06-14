# AI DM Employee - Professional Customer Success AI Agent

A production-ready AI agent that behaves like a professional customer success representative for Instagram DM automation.

## Architecture

```
Incoming Message
       ↓
Conversation Memory
       ↓
Business Context
       ↓
Knowledge Base
       ↓
AI Processing
       ↓
Safety Validation
       ↓
Moderation Layer
       ↓
Hallucination Prevention
       ↓
Response
       ↓
Conversation Storage
```

## Features

### Conversation Memory
- **Previous Chats**: Remembers conversation history
- **Resources Shared**: Tracks what has been shared with customers
- **Customer Interests**: Learns and stores customer preferences
- **FAQ History**: Tracks which FAQs have been asked
- **Lead Status**: Maintains and updates lead qualification
- **Business Context**: Stores business-specific information

### Knowledge Sources
- Website content
- PDF documents
- Brochures
- Catalogs
- Menus
- FAQ entries
- Portfolio items
- GitHub repositories
- YouTube videos
- Manual knowledge base

### Capabilities
- **Natural Conversations**: Context-aware responses
- **Resource Recommendations**: Suggests relevant materials
- **Appointment Suggestions**: Proposes meeting times
- **Lead Qualification**: Scores and qualifies leads
- **Question Answering**: Answers from knowledge base
- **Context Awareness**: Understands conversation flow
- **Human Takeover**: Escalates to humans when needed
- **Conversation History**: Maintains full history

### Provider Support
- Gemini
- OpenAI
- Claude
- Ollama
- Qwen
- Llama
- Gemma
- Mistral

### Enterprise Features
- **Retry Logic**: Automatic retries with exponential backoff
- **Timeout Handling**: Configurable timeouts
- **AI Logs**: Comprehensive logging for debugging
- **Moderation Layer**: Content policy enforcement
- **Hallucination Prevention**: Verifies responses against knowledge base
- **Safety Validation**: Input/output safety checks

## Installation

The AI DM Employee is part of the existing DM_tool project. No additional installation required.

## Usage

### 1. Initialize the AI DM Employee

```python
from services.ai_dm_employee import AIDMEmployee
from services.ai_dm_employee.business_context import BusinessContext

# Create business context
business_context = BusinessContext(
    business_id="your_business_id",
    business_name="Your Business Name",
    business_type="Retail",
    industry="E-commerce",
    description="Your business description",
    website="https://yourwebsite.com",
    email="contact@yourwebsite.com",
    phone="+1234567890",
    products=[
        {"name": "Product 1", "description": "...", "price": "$99"},
        {"name": "Product 2", "description": "...", "price": "$149"},
    ],
    services=[
        {"name": "Consultation", "description": "..."},
    ],
    faq=[
        {"question": "What are your hours?", "answer": "We're open 9-5 PM."},
        {"question": "Do you ship internationally?", "answer": "Yes, we ship worldwide."},
    ],
    ai_personality="professional",
    ai_tone="friendly",
)

# Get AI provider manager (from existing infrastructure)
ai_provider_manager = app.config.get("AI_PROVIDER_MANAGER")

# Create AI DM Employee
employee = AIDMEmployee(
    business_id="your_business_id",
    business_context=business_context,
    ai_provider_manager=ai_provider_manager,
    config={
        "temperature": 0.7,
        "max_tokens": 500,
        "model": "gpt-4",
    },
)
```

### 2. Process Messages

```python
result = await employee.process_message(
    conversation_id="conv_123",
    user_id="user_456",
    username="customer_handle",
    message="Hi! I'm interested in your products.",
)

print(result.response)
print(f"Confidence: {result.confidence}")
print(f"Intent: {result.intent}")
print(f"Requires Human: {result.requires_human}")
```

### 3. Set Up Human Takeover Callback

```python
async def handle_human_takeover(conversation_id: str, reason: str, message: str):
    # Notify human agents via Slack, email, etc.
    await send_notification_to_agents(conversation_id, reason, message)

employee.set_human_takeover_callback(handle_human_takeover)
```

## API Endpoints

### Initialize AI DM Employee
```
POST /api/ai-dm/initialize
{
    "business_id": "...",
    "business_name": "...",
    "business_type": "...",
    "industry": "...",
    "description": "...",
    "website": "...",
    "email": "...",
    "phone": "...",
    "products": [...],
    "services": [...],
    "faq": [...],
    "ai_personality": "professional",
    "ai_tone": "friendly"
}
```

### Process Message
```
POST /api/ai-dm/process
{
    "business_id": "...",
    "conversation_id": "...",
    "user_id": "...",
    "username": "...",
    "message": "Hi, I'm interested in..."
}
```

### Search Knowledge Base
```
GET /api/ai-dm/knowledge/search?business_id=...&q=pricing&limit=10
```

### Add Knowledge
```
POST /api/ai-dm/knowledge/add
{
    "business_id": "...",
    "type": "faq",
    "content": "Q: How do I return an item?\nA: Contact us within 30 days...",
    "title": "Return Policy",
    "tags": ["returns", "policy"]
}
```

### Get Statistics
```
GET /api/ai-dm/statistics?business_id=...
```

## Configuration

### AI Configuration
```python
config = {
    "temperature": 0.7,      # Response creativity (0.0-1.0)
    "max_tokens": 500,        # Maximum response length
    "model": "gpt-4",         # Model to use
    "provider": "openai",     # Provider to use
}
```

### Safety Configuration
```python
# Configure blocked topics
employee.safety_validator.configure(
    blocked_topics=["politics", "religion"],
    offensive_words=["spam", "scam"],
)

# Configure moderation level
employee.moderation_layer.set_level(ModerationLevel.STRICT)
```

### Hallucination Prevention
```python
employee.hallucination_prevention.configure(
    min_confidence=0.6,       # Minimum confidence threshold
    strict_mode=False,        # Block low confidence responses
    claim_verification=True,   # Verify factual claims
)
```

## Intent Detection

The AI DM Employee automatically detects the following intents:

| Intent | Description | Triggers |
|--------|-------------|----------|
| `greeting` | Hello/hi messages | Hi, Hello, Hey |
| `pricing_inquiry` | Questions about prices | Price, cost, how much |
| `purchase_intent` | Interest in buying | Buy, order, interested |
| `product_inquiry` | Questions about products | Product, what do you offer |
| `service_inquiry` | Questions about services | Service, help, support |
| `appointment_request` | Scheduling meetings | Appointment, schedule, book |
| `faq` | General questions | When, where, what, how |
| `complaint` | Negative feedback | Problem, issue, disappointed |
| `feedback` | Reviews/suggestions | Feedback, review, suggestion |
| `goodbye` | Closing conversation | Bye, thanks, goodbye |
| `human_request` | Request for human | Human, agent, real person |

## Lead Status

Automatically qualifies and updates lead status:

| Status | Description |
|--------|-------------|
| `new` | New conversation started |
| `interested` | Showed purchase intent |
| `qualified` | Meets lead criteria |
| `proposal` | Proposal sent |
| `negotiation` | In negotiation |
| `won` | Deal closed |
| `lost` | Deal lost |

## Safety Categories

The safety validator checks for:

- **Harassment**: Offensive language directed at individuals
- **Hate Speech**: Discriminatory content
- **Sexual Content**: Adult or inappropriate sexual content
- **Violence**: Violent threats or descriptions
- **Self-Harm**: Content about self-harm
- **Dangerous Content**: Instructions for harmful activities
- **Misinformation**: False or misleading claims
- **Sensitive Data**: Personal information patterns
- **Commercial Spam**: Excessive promotional content
- **Off-Topic**: Blocked topic content

## Hallucination Prevention

Prevents the AI from fabricating information:

1. **Claim Extraction**: Identifies factual statements
2. **Knowledge Verification**: Checks against knowledge base
3. **Confidence Scoring**: Rates response confidence
4. **Safe Alternatives**: Provides fallback responses
5. **Source Citations**: References knowledge sources

## Logging

Comprehensive logging for debugging and compliance:

```python
# Access logs
entries = logging_service.get_entries(
    conversation_id="conv_123",
    level=LogLevel.ERROR,
    limit=100,
)

# Get session logs
session_logs = logging_service.get_session_logs("session_456")

# Export logs
logs_export = logging_service.export_logs(
    format="json",
    start_time=datetime(2024, 1, 1),
)
```

## Production Deployment

### 1. Set Up AI Providers
Configure your preferred AI providers in the existing AI provider infrastructure.

### 2. Initialize on Startup
```python
# In your app initialization
from services.ai_dm_employee import AIDMEmployee

def init_ai_dm_employees(app):
    employees = {}
    
    for business in Business.query.filter_by(is_active=True).all():
        business_context = create_business_context(business)
        
        employees[business.id] = AIDMEmployee(
            business_id=business.id,
            business_context=business_context,
            ai_provider_manager=app.config["AI_PROVIDER_MANAGER"],
        )
    
    app.config["AI_DM_EMPLOYEES"] = employees
```

### 3. Webhook Integration
```python
# In your Instagram webhook handler
@instagram_bp.route("/webhook", methods=["POST"])
def handle_instagram_webhook():
    data = request.json
    
    if data.get("entry"):
        for entry in data["entry"]:
            for message in entry.get("messages", []):
                # Process with AI DM Employee
                result = process_with_ai_dm_employee(message)
                
                if result.should_send:
                    send_instagram_message(result.response)
    
    return "", 200
```

## Testing

```python
# Test intent detection
employee = AIDMEmployee(...)
intent, entities = employee._detect_intent("Hi! What are your hours?")
assert intent == "faq"

# Test safety validation
result = employee.safety_validator.validate_input("Hello!")
assert result.is_safe

# Test hallucination prevention
check = employee.hallucination_prevention.check_response(
    response="We offer 24/7 support.",
    business_id="test",
    user_query="Do you offer support?",
)
assert check.score > 0.5
```

## License

Part of the DM_tool project.
