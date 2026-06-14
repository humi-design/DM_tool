"""Hallucination Prevention - Verifies AI responses against knowledge base."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Set, Tuple
from enum import Enum
import re


class ConfidenceLevel(Enum):
    """Confidence levels for responses."""
    HIGH = "high"      # Verified against knowledge base
    MEDIUM = "medium"  # Likely accurate, some uncertainty
    LOW = "low"       # Potential hallucination risk
    UNVERIFIABLE = "unverifiable"  # Cannot verify against known data


@dataclass
class HallucinationCheck:
    """Result of a hallucination check."""
    is_verified: bool
    confidence: ConfidenceLevel
    score: float
    verified_facts: List[str] = field(default_factory=list)
    unverified_claims: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    citations: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class FactCheck:
    """A factual claim to verify."""
    claim: str
    context: str = ""
    verified: bool = False
    verification_source: Optional[str] = None
    confidence: float = 0.0


class HallucinationPrevention:
    """Prevents and detects hallucinations in AI responses.
    
    Responsibilities:
    - Verify claims against knowledge base
    - Check for unverified information
    - Score response confidence
    - Provide citations from knowledge base
    - Suggest fact-checking for uncertain claims
    """
    
    # Patterns for factual claims
    FACT_PATTERNS = [
        r'(?:we|our company|this business)\s+(?:offer|provide|have|give|sell|is|are)',
        r'(?:our|we)\s+\w+\s+(?:costs?|starts? at|includes?|covers?)',
        r'(?:you can|you will|you\'ll|you\'re able to)',
        r'\b\d+(?:\s*(?:hours?|days?|weeks?|months?|years?))?\b',  # Numbers with time
        r'\b(?:always|never|every|all|none)\b',
        r'\b(?:free|guaranteed|100%|instant|immediate)\b',
        r'\b(?:price|cost|fee|charge|rate)\s*(?:is|starts?|begins?)\b',
    ]
    
    # Quantifiers that may indicate overconfidence
    OVERCONFIDENCE_PATTERNS = [
        r'\bdefinitely\b',
        r'\babsolutely\b',
        r'\bcertainly\b',
        r'\b100%\b',
        r'\bguaranteed\b',
        r'\bwithout a doubt\b',
        r'\bbest ever\b',
    ]
    
    def __init__(self):
        """Initialize the hallucination prevention system."""
        self._compile_patterns()
        
        # Knowledge base reference (set externally)
        self._knowledge_base = None
        
        # Configuration
        self.min_confidence_threshold = 0.6
        self.claim_verification_enabled = True
        self.strict_mode = False
        
        # Response templates for fallback
        self._fallback_templates = [
            "I don't have specific information about that. Would you like me to find out more?",
            "I'm not certain about that detail. Could you provide more context or check our website?",
            "That's outside my current knowledge. I recommend reaching out directly for accurate information.",
        ]
        
        # Statistics
        self._stats = {
            "total_checks": 0,
            "verified_responses": 0,
            "flagged_responses": 0,
            "blocked_responses": 0,
        }
    
    def _compile_patterns(self) -> None:
        """Compile regex patterns."""
        self._fact_re = [re.compile(p, re.IGNORECASE) for p in self.FACT_PATTERNS]
        self._overconfidence_re = [re.compile(p, re.IGNORECASE) for p in self.OVERCONFIDENCE_PATTERNS]
    
    def set_knowledge_base(self, knowledge_base) -> None:
        """Set the knowledge base reference.
        
        Args:
            knowledge_base: KnowledgeBaseService instance
        """
        self._knowledge_base = knowledge_base
    
    def configure(
        self,
        min_confidence: float = 0.6,
        strict_mode: bool = False,
        claim_verification: bool = True,
    ) -> None:
        """Configure hallucination prevention.
        
        Args:
            min_confidence: Minimum confidence threshold
            strict_mode: Enable strict verification
            claim_verification: Enable claim verification
        """
        self.min_confidence_threshold = min_confidence
        self.strict_mode = strict_mode
        self.claim_verification_enabled = claim_verification
    
    def check_response(
        self,
        response: str,
        business_id: str,
        user_query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> HallucinationCheck:
        """Check an AI response for hallucinations.
        
        Args:
            response: AI response to check
            business_id: Business identifier
            user_query: Original user query
            context: Optional additional context
            
        Returns:
            HallucinationCheck with verification details
        """
        self._stats["total_checks"] += 1
        
        verified_facts = []
        unverified_claims = []
        warnings = []
        suggestions = []
        citations = []
        
        # Extract factual claims from response
        claims = self._extract_claims(response)
        
        # Check each claim
        for claim in claims:
            verification = self._verify_claim(claim, business_id, user_query)
            
            if verification.verified:
                verified_facts.append(claim)
                if verification.verification_source:
                    citations.append({
                        "claim": claim,
                        "source": verification.verification_source,
                        "confidence": verification.confidence,
                    })
            else:
                unverified_claims.append(claim)
                suggestions.append(
                    f"Verify or rephrase: '{claim}'. "
                    f"Consider using softer language like 'based on our information...' or 'typically...'"
                )
        
        # Check for overconfidence indicators
        overconfidence_issues = self._check_overconfidence(response)
        warnings.extend(overconfidence_issues)
        
        # Check for specificity without verification
        if self._has_specific_claims(response) and not verified_facts:
            warnings.append("Response contains specific claims that could not be verified")
        
        # Calculate confidence score
        confidence = self._calculate_confidence(
            response=response,
            verified_facts=verified_facts,
            unverified_claims=unverified_claims,
            overconfidence_issues=overconfidence_issues,
        )
        
        # Determine confidence level
        if confidence >= 0.8 and not unverified_claims:
            level = ConfidenceLevel.HIGH
            is_verified = True
        elif confidence >= 0.6 and len(unverified_claims) <= 2:
            level = ConfidenceLevel.MEDIUM
            is_verified = False
        elif confidence >= 0.4:
            level = ConfidenceLevel.LOW
            is_verified = False
        else:
            level = ConfidenceLevel.UNVERIFIABLE
            is_verified = False
        
        # Update stats
        if is_verified:
            self._stats["verified_responses"] += 1
        elif confidence < self.min_confidence_threshold:
            self._stats["flagged_responses"] += 1
            if self.strict_mode:
                self._stats["blocked_responses"] += 1
        
        return HallucinationCheck(
            is_verified=is_verified,
            confidence=level,
            score=confidence,
            verified_facts=verified_facts,
            unverified_claims=unverified_claims,
            warnings=warnings,
            suggestions=suggestions,
            citations=citations,
        )
    
    def _extract_claims(self, text: str) -> List[str]:
        """Extract factual claims from text.
        
        Args:
            text: Text to extract from
            
        Returns:
            List of claims
        """
        claims = []
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check if sentence contains fact patterns
            for pattern in self._fact_re:
                if pattern.search(sentence):
                    claims.append(sentence)
                    break
            
            # Also check for specific numbers/statistics
            if re.search(r'\b\d+(?:\.\d+)?(?:\s*(?:percent|%|dollars|\$|hours?|days?))?\b', sentence):
                if sentence not in claims:
                    claims.append(sentence)
        
        return claims
    
    def _verify_claim(
        self,
        claim: str,
        business_id: str,
        query: str,
    ) -> FactCheck:
        """Verify a factual claim against knowledge base.
        
        Args:
            claim: Claim to verify
            business_id: Business identifier
            query: Original query for context
            
        Returns:
            FactCheck with verification result
        """
        if not self._knowledge_base:
            # No knowledge base, cannot verify
            return FactCheck(claim=claim, confidence=0.0)
        
        # Search for relevant information
        search_results = self._knowledge_base.search(
            business_id=business_id,
            query=claim,
            top_k=3,
            min_score=0.1,
        )
        
        if not search_results:
            # No relevant information found
            return FactCheck(
                claim=claim,
                confidence=0.0,
                verified=False,
            )
        
        # Check if any result strongly supports the claim
        for result in search_results:
            content_lower = result.document.content.lower()
            claim_lower = claim.lower()
            
            # Check for matching key terms
            claim_words = set(re.findall(r'\b\w{4,}\b', claim_lower))
            content_words = set(re.findall(r'\b\w{4,}\b', content_lower))
            
            overlap = len(claim_words & content_words) / max(1, len(claim_words))
            
            if overlap >= 0.5:
                return FactCheck(
                    claim=claim,
                    verified=True,
                    verification_source=result.document.title or result.document.source,
                    confidence=result.score * overlap,
                )
        
        return FactCheck(claim=claim, confidence=0.3, verified=False)
    
    def _check_overconfidence(self, text: str) -> List[str]:
        """Check for overconfidence indicators.
        
        Args:
            text: Text to check
            
        Returns:
            List of warnings
        """
        warnings = []
        
        for pattern in self._overconfidence_re:
            matches = pattern.findall(text)
            if matches:
                warnings.append(
                    f"Overconfidence indicator detected: '{matches[0]}'. "
                    f"Consider using softer language."
                )
        
        return warnings
    
    def _has_specific_claims(self, text: str) -> bool:
        """Check if text has specific claims.
        
        Args:
            text: Text to check
            
        Returns:
            True if specific claims detected
        """
        # Check for numbers/statistics
        if re.search(r'\b\d+(?:\.\d+)?\s*(?:percent|%|dollars|\$)\b', text):
            return True
        
        # Check for specific times
        if re.search(r'\b(?:monday|tuesday|...|sunday|january|...|december)\b', text, re.IGNORECASE):
            return True
        
        # Check for prices
        if re.search(r'\$\d+', text):
            return True
        
        return False
    
    def _calculate_confidence(
        self,
        response: str,
        verified_facts: List[str],
        unverified_claims: List[str],
        overconfidence_issues: List[str],
    ) -> float:
        """Calculate overall confidence score.
        
        Args:
            response: Response text
            verified_facts: List of verified facts
            unverified_claims: List of unverified claims
            overconfidence_issues: List of overconfidence warnings
            
        Returns:
            Confidence score between 0 and 1
        """
        # Base score
        score = 1.0
        
        # Reduce for unverified claims
        if unverified_claims:
            # Each unverified claim reduces score
            deduction = min(0.4, len(unverified_claims) * 0.15)
            score -= deduction
        
        # Reduce for overconfidence
        if overconfidence_issues:
            score -= min(0.2, len(overconfidence_issues) * 0.1)
        
        # Increase for verified facts
        if verified_facts:
            bonus = min(0.2, len(verified_facts) * 0.05)
            score += bonus
        
        # Reduce if response is too short
        if len(response.split()) < 10:
            score -= 0.1
        
        # Reduce if response is too long with few verified facts
        if len(response.split()) > 100 and len(verified_facts) < 2:
            score -= 0.1
        
        return max(0.0, min(1.0, score))
    
    def get_safe_alternative(
        self,
        response: str,
        check: HallucinationCheck,
        user_query: str,
    ) -> str:
        """Get a safer alternative response.
        
        Args:
            response: Original response
            check: HallucinationCheck result
            user_query: Original user query
            
        Returns:
            Safer response
        """
        if check.is_verified:
            return response
        
        # If very low confidence, use fallback
        if check.confidence == ConfidenceLevel.UNVERIFIABLE:
            return self._get_fallback_response(user_query)
        
        # Try to improve the response
        improved = response
        
        # Add hedging language for unverified claims
        for claim in check.unverified_claims:
            # Add uncertainty markers
            improved = improved.replace(
                claim,
                f"I believe {claim.lower()}, though you may want to verify this directly."
            )
        
        # Add disclaimer
        if check.warnings:
            disclaimer = "\n\n_I'm committed to providing accurate information. "
            if check.citations:
                disclaimer += f"This is based on our official materials. "
            disclaimer += "For the most current details, please check our website or contact us directly._"
            improved += disclaimer
        
        return improved
    
    def _get_fallback_response(self, query: str) -> str:
        """Get a fallback response when confidence is too low.
        
        Args:
            query: Original user query
            
        Returns:
            Safe fallback response
        """
        # Try to personalize based on query
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['price', 'cost', 'how much']):
            return (
                "I don't have specific pricing information available right now. "
                "For the most accurate pricing, I'd recommend checking our website "
                "or reaching out to our team directly. They'd be happy to provide "
                "a personalized quote based on your needs!"
            )
        
        if any(word in query_lower for word in ['hour', 'open', 'close', 'when', 'time']):
            return (
                "I don't have our current hours handy. For the most accurate "
                "information, please check our website or give us a call. "
                "We're always happy to help!"
            )
        
        if any(word in query_lower for word in ['where', 'location', 'address', 'directions']):
            return (
                "I'd love to help with directions! For our most current location "
                "details, please visit our website or let me know if you'd like "
                "our contact information."
            )
        
        # Generic fallback
        import random
        return random.choice(self._fallback_templates)
    
    def should_block_response(self, check: HallucinationCheck) -> Tuple[bool, str]:
        """Determine if a response should be blocked.
        
        Args:
            check: HallucinationCheck result
            
        Returns:
            Tuple of (should_block, reason)
        """
        # In strict mode with very low confidence
        if self.strict_mode and check.confidence == ConfidenceLevel.UNVERIFIABLE:
            return True, "Response contains unverifiable claims in strict mode"
        
        # If score is below threshold
        if check.score < self.min_confidence_threshold * 0.5:
            return True, "Confidence score too low"
        
        # If more than half of claims are unverified
        total_claims = len(check.verified_facts) + len(check.unverified_claims)
        if total_claims > 0:
            unverified_ratio = len(check.unverified_claims) / total_claims
            if unverified_ratio > 0.7:
                return True, "Too many unverified claims"
        
        return False, ""
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get hallucination prevention statistics.
        
        Returns:
            Statistics dictionary
        """
        total = max(1, self._stats["total_checks"])
        return {
            **self._stats,
            "verification_rate": self._stats["verified_responses"] / total,
            "flag_rate": self._stats["flagged_responses"] / total,
            "block_rate": self._stats["blocked_responses"] / total,
            "min_confidence_threshold": self.min_confidence_threshold,
            "strict_mode": self.strict_mode,
        }
    
    def reset_statistics(self) -> None:
        """Reset statistics."""
        self._stats = {
            "total_checks": 0,
            "verified_responses": 0,
            "flagged_responses": 0,
            "blocked_responses": 0,
        }
