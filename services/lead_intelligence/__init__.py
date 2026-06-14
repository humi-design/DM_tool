"""Lead Intelligence AI Service.

This module provides AI-powered features for lead management including:
- Automatic lead scoring based on multiple factors
- Lead categorization (hot/warm/cold)
- Conversation summarization
- AI-generated notes and insights
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from datetime import datetime
import re

from services.ai_provider.manager import AIManager
from services.ai_provider.base import Message, MessageRole


@dataclass
class LeadScoreResult:
    """Result of lead scoring analysis."""
    score: int  # 0-100
    confidence: float  # 0-1
    factors: Dict[str, int]  # Individual scoring factors
    reasons: List[str]  # Explanation of scoring
    recommendations: List[str]  # Suggested actions


@dataclass
class LeadSummary:
    """AI-generated lead summary."""
    summary: str  # Overall summary
    key_points: List[str]  # Key points about the lead
    intent_signals: List[str]  # Signals of purchase intent
    concerns: List[str]  # Potential concerns or objections
    next_steps: List[str]  # Suggested next steps


class LeadIntelligenceService:
    """AI-powered lead intelligence service."""
    
    # Scoring factor weights
    WEIGHTS = {
        "contact_info": 15,      # Has email, phone, company
        "engagement": 25,         # Conversation frequency
        "budget_indicator": 20,  # Budget mentioned or implied
        "intent_signals": 25,     # Purchase intent indicators
        "engagement_quality": 15  # Quality of interactions
    }
    
    def __init__(self, ai_manager: Optional[AIManager] = None):
        """Initialize the lead intelligence service.
        
        Args:
            ai_manager: Optional AI manager for advanced AI features
        """
        self.ai_manager = ai_manager
    
    def calculate_score(self, lead_data: Dict[str, Any]) -> LeadScoreResult:
        """Calculate lead score based on available data.
        
        Args:
            lead_data: Dictionary containing lead information
            
        Returns:
            LeadScoreResult with score and analysis
        """
        factors = {}
        reasons = []
        recommendations = []
        total_score = 0
        
        # Contact Information Score (15 points max)
        contact_score = 0
        if lead_data.get("email"):
            contact_score += 5
        if lead_data.get("phone"):
            contact_score += 5
        if lead_data.get("company"):
            contact_score += 5
        factors["contact_info"] = contact_score
        total_score += contact_score * (self.WEIGHTS["contact_info"] / 15)
        
        if contact_score >= 10:
            reasons.append("Complete contact information provided")
        elif contact_score > 0:
            reasons.append(f"Partial contact info ({contact_score}/15 fields)")
        
        # Engagement Score (25 points max)
        engagement_score = 0
        conv_count = lead_data.get("conversation_count", 0)
        if conv_count >= 10:
            engagement_score = 25
        elif conv_count >= 5:
            engagement_score = 20
        elif conv_count >= 3:
            engagement_score = 15
        elif conv_count >= 1:
            engagement_score = 10
        
        factors["engagement"] = engagement_score
        total_score += engagement_score * (self.WEIGHTS["engagement"] / 25)
        
        if conv_count > 0:
            reasons.append(f"{conv_count} conversation(s) recorded")
        else:
            reasons.append("No conversations yet")
        
        # Budget Indicator Score (20 points max)
        budget_score = 0
        budget = lead_data.get("budget", "")
        interest = lead_data.get("interest", "")
        requirements = lead_data.get("requirements", "")
        
        if budget:
            budget_score = 15
            # Check for specific budget ranges
            if any(x in budget.lower() for x in ["10,000", "10k", "high", "premium", "enterprise"]):
                budget_score = 20
                reasons.append("High budget indicated")
            elif any(x in budget.lower() for x in ["5,000", "5k", "mid"]):
                budget_score = 17
                reasons.append("Mid-range budget indicated")
            else:
                reasons.append("Budget information provided")
        elif interest or requirements:
            budget_score = 10
            reasons.append("Interest/requirements mentioned")
        
        factors["budget_indicator"] = budget_score
        total_score += budget_score * (self.WEIGHTS["budget_indicator"] / 20)
        
        # Intent Signals Score (25 points max)
        intent_score = 0
        combined_text = f"{interest} {requirements} {lead_data.get('notes', '')}".lower()
        
        # High intent keywords
        high_intent = ["buy", "purchase", "order", "subscribe", "sign up", "get started", 
                       "pricing", "cost", "how much", "demo", "trial", "interested"]
        medium_intent = ["looking", "need", "want", "considering", "evaluating", "compare",
                        "research", "options", "features", "benefits"]
        
        high_intent_count = sum(1 for kw in high_intent if kw in combined_text)
        medium_intent_count = sum(1 for kw in medium_intent if kw in combined_text)
        
        intent_score = min(25, high_intent_count * 8 + medium_intent_count * 4)
        factors["intent_signals"] = intent_score
        total_score += intent_score * (self.WEIGHTS["intent_signals"] / 25)
        
        if intent_score >= 15:
            reasons.append("Strong purchase intent signals detected")
        elif intent_score > 0:
            reasons.append(f"Intent signals found ({intent_score}/25)")
        
        # Engagement Quality Score (15 points max)
        quality_score = 0
        if lead_data.get("last_conversation_at"):
            days_since = (datetime.utcnow() - lead_data["last_conversation_at"]).days
            if days_since <= 1:
                quality_score = 15
                reasons.append("Recent engagement (within 24h)")
            elif days_since <= 7:
                quality_score = 12
                reasons.append("Recent engagement (within 7 days)")
            elif days_since <= 30:
                quality_score = 8
            else:
                quality_score = 3
                recommendations.append("Re-engagement recommended")
        
        if lead_data.get("source_type") in ["dm", "comment", "referral"]:
            quality_score += 2
        
        factors["engagement_quality"] = min(15, quality_score)
        total_score += min(15, quality_score) * (self.WEIGHTS["engagement_quality"] / 15)
        
        # Generate recommendations
        if total_score < 30:
            recommendations.append("Send welcome sequence")
            recommendations.append("Share educational content")
        elif total_score < 60:
            recommendations.append("Schedule follow-up call")
            recommendations.append("Share case studies or testimonials")
        else:
            recommendations.append("Prioritize for sales outreach")
            recommendations.append("Prepare personalized proposal")
        
        # Calculate confidence (based on data completeness)
        confidence = min(1.0, (contact_score + 5) / 20 * 0.3 + 
                       (conv_count + 1) / 11 * 0.4 +
                       (budget_score + 5) / 25 * 0.3)
        
        return LeadScoreResult(
            score=min(100, int(total_score)),
            confidence=round(confidence, 2),
            factors=factors,
            reasons=reasons,
            recommendations=recommendations
        )
    
    def categorize_lead(self, score: int) -> str:
        """Categorize lead based on score.
        
        Args:
            score: Lead score (0-100)
            
        Returns:
            'hot', 'warm', or 'cold'
        """
        if score >= 65:
            return "hot"
        elif score >= 35:
            return "warm"
        return "cold"
    
    async def generate_summary(self, lead_data: Dict[str, Any], 
                               conversation_history: List[Dict[str, str]] = None) -> LeadSummary:
        """Generate AI-powered summary of the lead.
        
        Args:
            lead_data: Lead information dictionary
            conversation_history: Optional list of conversation messages
            
        Returns:
            LeadSummary with AI-generated insights
        """
        if not self.ai_manager:
            return self._generate_rule_based_summary(lead_data, conversation_history)
        
        # Build context for AI
        context = self._build_summary_context(lead_data, conversation_history)
        
        try:
            messages = [
                Message(
                    role=MessageRole.SYSTEM,
                    content="You are a sales intelligence analyst. Analyze the lead data and conversation history to provide insights. Format your response as JSON with: summary, key_points[], intent_signals[], concerns[], next_steps[]"
                ),
                Message(
                    role=MessageRole.USER,
                    content=context
                )
            ]
            
            response = await self.ai_manager.chat(messages)
            return self._parse_summary_response(response.content, lead_data)
        except Exception as e:
            return self._generate_rule_based_summary(lead_data, conversation_history)
    
    def _build_summary_context(self, lead_data: Dict[str, Any], 
                               conversation_history: List[Dict[str, str]] = None) -> str:
        """Build context string for AI summary."""
        context_parts = []
        
        # Basic info
        context_parts.append("LEAD INFORMATION:")
        for key in ["name", "email", "company", "phone", "budget", "interest", "requirements", "source_type"]:
            if lead_data.get(key):
                context_parts.append(f"  {key}: {lead_data[key]}")
        
        # Engagement info
        context_parts.append(f"\nEngagement: {lead_data.get('conversation_count', 0)} conversations")
        if lead_data.get("last_conversation_at"):
            context_parts.append(f"Last contact: {lead_data['last_conversation_at']}")
        
        # Notes
        if lead_data.get("notes"):
            context_parts.append(f"\nNotes: {lead_data['notes']}")
        
        # Conversation history
        if conversation_history:
            context_parts.append("\nCONVERSATION HISTORY:")
            for i, msg in enumerate(conversation_history[-10:], 1):  # Last 10 messages
                role = msg.get("role", "unknown")
                text = msg.get("text", "")[:200]  # Truncate
                context_parts.append(f"  [{role}]: {text}")
        
        return "\n".join(context_parts)
    
    def _parse_summary_response(self, response: str, lead_data: Dict[str, Any]) -> LeadSummary:
        """Parse AI response into LeadSummary."""
        try:
            import json
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return LeadSummary(
                    summary=data.get("summary", ""),
                    key_points=data.get("key_points", []),
                    intent_signals=data.get("intent_signals", []),
                    concerns=data.get("concerns", []),
                    next_steps=data.get("next_steps", [])
                )
        except Exception:
            pass
        
        # Fallback to rule-based
        return self._generate_rule_based_summary(lead_data, None)
    
    def _generate_rule_based_summary(self, lead_data: Dict[str, Any],
                                    conversation_history: List[Dict[str, str]] = None) -> LeadSummary:
        """Generate summary using rule-based approach."""
        key_points = []
        intent_signals = []
        concerns = []
        next_steps = []
        
        # Extract key points from available data
        if lead_data.get("name"):
            key_points.append(f"Lead name: {lead_data['name']}")
        
        if lead_data.get("company"):
            key_points.append(f"Company: {lead_data['company']}")
        
        if lead_data.get("source_type"):
            key_points.append(f"Source: {lead_data['source_type']}")
        
        # Budget and interest
        if lead_data.get("budget"):
            key_points.append(f"Budget: {lead_data['budget']}")
            if any(x in lead_data["budget"].lower() for x in ["high", "10,000", "enterprise"]):
                intent_signals.append("High budget indicates serious intent")
        
        if lead_data.get("interest"):
            key_points.append(f"Interest: {lead_data['interest']}")
            intent_signals.append("Interest area identified")
        
        if lead_data.get("requirements"):
            key_points.append(f"Requirements: {lead_data['requirements']}")
        
        # Engagement analysis
        conv_count = lead_data.get("conversation_count", 0)
        if conv_count > 0:
            key_points.append(f"{conv_count} conversation(s) recorded")
            if conv_count >= 5:
                intent_signals.append("High engagement level")
        
        # Check for concerns
        if not lead_data.get("email"):
            concerns.append("Missing email address")
        if not lead_data.get("phone"):
            concerns.append("Missing phone number")
        if not lead_data.get("budget"):
            concerns.append("Budget not specified")
        
        # Generate next steps
        if conv_count == 0:
            next_steps.append("Send initial outreach message")
            next_steps.append("Introduce product/service value proposition")
        elif conv_count < 3:
            next_steps.append("Continue nurturing conversation")
            next_steps.append("Gather more requirements information")
        else:
            next_steps.append("Schedule discovery call")
            next_steps.append("Prepare customized proposal")
        
        # Build summary
        score = lead_data.get("lead_score", 50)
        if score >= 65:
            summary = f"High-potential lead identified. {lead_data.get('name', 'This lead')} from {lead_data.get('company', 'unknown company')} shows strong engagement signals."
        elif score >= 35:
            summary = f"Medium-potential lead requiring further nurturing. {lead_data.get('name', 'This lead')} has shown some interest but needs follow-up."
        else:
            summary = f"Low-potential lead for long-term nurturing. {lead_data.get('name', 'This lead')} may need more education about the product/service."
        
        return LeadSummary(
            summary=summary,
            key_points=key_points,
            intent_signals=intent_signals,
            concerns=concerns,
            next_steps=next_steps
        )
    
    async def generate_notes(self, lead_data: Dict[str, Any],
                            conversation_history: List[Dict[str, str]] = None) -> str:
        """Generate AI-powered notes for the lead.
        
        Args:
            lead_data: Lead information dictionary
            conversation_history: Optional list of conversation messages
            
        Returns:
            AI-generated notes as string
        """
        if not self.ai_manager:
            return self._generate_rule_based_notes(lead_data)
        
        try:
            context = self._build_summary_context(lead_data, conversation_history)
            
            messages = [
                Message(
                    role=MessageRole.SYSTEM,
                    content="You are a sales assistant helping to generate notes about leads. Analyze the data and generate concise, actionable notes. Focus on key insights, pain points, and recommendations."
                ),
                Message(
                    role=MessageRole.USER,
                    content=context
                )
            ]
            
            response = await self.ai_manager.chat(messages)
            return response.content.strip()
        except Exception:
            return self._generate_rule_based_notes(lead_data)
    
    def _generate_rule_based_notes(self, lead_data: Dict[str, Any]) -> str:
        """Generate notes using rule-based approach."""
        notes = []
        
        # Profile summary
        name = lead_data.get("name", "Unknown")
        company = lead_data.get("company", "Unknown company")
        notes.append(f"## Lead Profile\n- Name: {name}\n- Company: {company}")
        
        # Contact info
        contact_info = []
        if lead_data.get("email"):
            contact_info.append(f"Email: {lead_data['email']}")
        if lead_data.get("phone"):
            contact_info.append(f"Phone: {lead_data['phone']}")
        if contact_info:
            notes.append(f"\n## Contact Information\n- " + "\n- ".join(contact_info))
        
        # Interest and requirements
        if lead_data.get("interest"):
            notes.append(f"\n## Interest Area\n{lead_data['interest']}")
        
        if lead_data.get("requirements"):
            notes.append(f"\n## Requirements\n{lead_data['requirements']}")
        
        if lead_data.get("budget"):
            notes.append(f"\n## Budget\n{lead_data['budget']}")
        
        # Engagement summary
        conv_count = lead_data.get("conversation_count", 0)
        notes.append(f"\n## Engagement\n{conv_count} conversation(s)")
        
        # Recommendations
        score = lead_data.get("lead_score", 50)
        notes.append(f"\n## Next Steps\n- Lead Score: {score}/100")
        
        if score >= 65:
            notes.append("- Priority: HIGH - Schedule immediate follow-up")
            notes.append("- Prepare personalized proposal")
        elif score >= 35:
            notes.append("- Priority: MEDIUM - Continue nurturing")
            notes.append("- Share relevant case studies")
        else:
            notes.append("- Priority: LOW - Add to nurture sequence")
            notes.append("- Provide educational content")
        
        return "\n".join(notes)
    
    def analyze_conversation_sentiment(self, conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """Analyze sentiment and patterns in conversation history.
        
        Args:
            conversation_history: List of conversation messages
            
        Returns:
            Dictionary with sentiment analysis results
        """
        if not conversation_history:
            return {"sentiment": "neutral", "score": 0.5, "patterns": []}
        
        positive_keywords = ["thank", "great", "perfect", "love", "excellent", "amazing", 
                           "interested", "excited", "yes", "sure", "absolutely", "definitely"]
        negative_keywords = ["no", "not", "never", "can't", "don't", "won't", "sorry",
                            "busy", "later", "maybe", "concern", "worry", "issue"]
        
        positive_count = 0
        negative_count = 0
        total_messages = len(conversation_history)
        
        patterns = []
        
        for msg in conversation_history:
            text = msg.get("text", "").lower()
            
            positive_count += sum(1 for kw in positive_keywords if kw in text)
            negative_count += sum(1 for kw in negative_keywords if kw in text)
            
            # Detect specific patterns
            if "?" in text and msg.get("role") == "user":
                patterns.append("User asking questions - seeking information")
            if any(x in text for x in ["price", "cost", "pricing"]):
                patterns.append("Discussing pricing - evaluation phase")
            if any(x in text for x in ["timeline", "when", "start", "begin"]):
                patterns.append("Discussing timeline - planning phase")
            if any(x in text for x in ["competitor", "alternative", "other options"]):
                patterns.append("Comparing options - decision phase")
        
        # Calculate sentiment score
        total_sentiment = positive_count + negative_count
        if total_sentiment > 0:
            sentiment_score = positive_count / total_sentiment
        else:
            sentiment_score = 0.5
        
        if sentiment_score >= 0.7:
            sentiment = "very_positive"
        elif sentiment_score >= 0.55:
            sentiment = "positive"
        elif sentiment_score >= 0.45:
            sentiment = "neutral"
        elif sentiment_score >= 0.3:
            sentiment = "negative"
        else:
            sentiment = "very_negative"
        
        return {
            "sentiment": sentiment,
            "score": round(sentiment_score, 2),
            "positive_count": positive_count,
            "negative_count": negative_count,
            "patterns": list(set(patterns)),
            "message_count": total_messages
        }
    
    def predict_conversion_probability(self, lead_data: Dict[str, Any]) -> float:
        """Predict probability of lead conversion.
        
        Args:
            lead_data: Lead information dictionary
            
        Returns:
            Probability of conversion (0-1)
        """
        score = lead_data.get("lead_score", 50) / 100
        
        # Engagement multiplier
        conv_count = lead_data.get("conversation_count", 0)
        engagement_multiplier = min(1.5, 1 + (conv_count * 0.05))
        
        # Recency multiplier
        recency_multiplier = 1.0
        if lead_data.get("last_conversation_at"):
            days_since = (datetime.utcnow() - lead_data["last_conversation_at"]).days
            if days_since <= 3:
                recency_multiplier = 1.2
            elif days_since <= 14:
                recency_multiplier = 1.0
            elif days_since <= 30:
                recency_multiplier = 0.8
            else:
                recency_multiplier = 0.5
        
        # Budget indicator
        budget_multiplier = 1.0
        if lead_data.get("budget"):
            budget_multiplier = 1.1
        
        # Calculate final probability
        probability = score * engagement_multiplier * recency_multiplier * budget_multiplier
        return min(0.99, max(0.01, probability))


# Singleton instance
_lead_intelligence_service = None

def get_lead_intelligence_service() -> LeadIntelligenceService:
    """Get singleton instance of LeadIntelligenceService."""
    global _lead_intelligence_service
    if _lead_intelligence_service is None:
        try:
            ai_manager = AIManager.get_instance()
        except Exception:
            ai_manager = None
        _lead_intelligence_service = LeadIntelligenceService(ai_manager)
    return _lead_intelligence_service