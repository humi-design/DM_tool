"""Moderation Layer - Content moderation and policy compliance."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Set
from enum import Enum
import re


class ModerationLevel(Enum):
    """Level of content moderation."""
    NONE = "none"
    LIGHT = "light"
    STANDARD = "standard"
    STRICT = "strict"


class PolicyViolation(Enum):
    """Types of policy violations."""
    PROFANITY = "profanity"
    SPAM = "spam"
    PERSONAL_INFO = "personal_info"
    INAPPROPRIATE_CONTENT = "inappropriate_content"
    COMPETITOR_MENTION = "competitor_mention"
    ILLEGAL_CONTENT = "illegal_content"
    UNAUTHORIZED_CLAIMS = "unauthorized_claims"
    SENSITIVE_TOPICS = "sensitive_topics"


@dataclass
class ModerationResult:
    """Result of content moderation."""
    is_approved: bool
    score: float = 1.0
    violations: List[Dict[str, Any]] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    sanitized_content: Optional[str] = None
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ModerationLayer:
    """Content moderation layer for AI DM responses.
    
    Responsibilities:
    - Filter profanity and inappropriate language
    - Detect spam patterns
    - Ensure policy compliance
    - Sanitize content when needed
    - Handle sensitive topics
    """
    
    # Common profanity patterns (sanitized list)
    PROFANITY_PATTERNS = [
        r'\b[f][\s*#@$]?[u\*]+[c\*]+[k\*]+[e\*]*[d\*]*[i\*]*[n\*]*[g\*]*\b',
        r'\b[s][\s*#@$]?[h\*]+[i\*]+[t\*]+[e\*]*\b',
        r'\b[a][\s*#@$]?[s\*]+[s\*]+[h\*]+[o\*]+[l\*]+[e\*]*\b',
        r'\b[b\*]+[i\*]+[t\*]+[c\*]+[h\*]+\b',
        r'\b[d\*]+[a\*]+[m\*]+[n\*]\b',
        r'\b[g\*]+[o\*]+[d\*]+[\s]+[d\*]+[a\*]+[m\*]+[n\*]\b',
    ]
    
    # Spam patterns
    SPAM_PATTERNS = [
        r'(?:click here|click now|visit our website)',
        r'(?:buy now|order now|limited time)',
        r'(?:free money|make \$.*?fast|earn .*?day)',
        r'(?:guaranteed|100%|risk free)',
        r'(?:act immediately|call now|don\'t miss)',
        r'(?:winner|congratulations|you\'ve won)',
        r'(?:unsubscribe|opt-out)',
        r'\b[A-Z]{10,}\b',  # ALL CAPS words
        r'[!]{3,}',  # Multiple exclamation marks
        r'\b(.+)\b\s+\1\b',  # Repeated words
    ]
    
    # Competitor keywords
    COMPETITOR_KEYWORDS = [
        'competitor', 'rival', 'alternative to', 'instead of',
        'unlike', 'compared to', 'other than',
    ]
    
    # Unauthorized claim patterns
    UNAUTHORIZED_CLAIMS = [
        r'\b(clinical|trials?|studies?|research)\s+(proved|proven|shows?|demonstrates?)\b',
        r'\bFDA approved\b',
        r'\b(cures?|treats?|heals?|remedies?)\s+\w+\b',
        r'\b(doctor recommended|medical professional)\b',
        r'\bguaranteed\s+\w+\b',
        r'\bpermanent\s+(solution|fix|cure)\b',
    ]
    
    def __init__(self, level: ModerationLevel = ModerationLevel.STANDARD):
        """Initialize the moderation layer.
        
        Args:
            level: Moderation level to apply
        """
        self.level = level
        self._compile_patterns()
        
        # Custom rules
        self._custom_blocked_words: Set[str] = set()
        self._custom_allowed_words: Set[str] = set()
        self._blocked_urls: Set[str] = set()
        self._allowed_urls: Set[str] = set()
        
        # Statistics
        self._stats = {
            "total_checked": 0,
            "total_blocked": 0,
            "total_modified": 0,
            "violations_by_type": {},
        }
    
    def _compile_patterns(self) -> None:
        """Compile regex patterns for performance."""
        self._profanity_re = [re.compile(p, re.IGNORECASE) for p in self.PROFANITY_PATTERNS]
        self._spam_re = [re.compile(p, re.IGNORECASE) for p in self.SPAM_PATTERNS]
        self._competitor_re = re.compile(
            '|'.join(self.COMPETITOR_KEYWORDS),
            re.IGNORECASE
        )
        self._unauthorized_claims_re = [
            re.compile(p, re.IGNORECASE) for p in self.UNAUTHORIZED_CLAIMS
        ]
    
    def set_level(self, level: ModerationLevel) -> None:
        """Set moderation level.
        
        Args:
            level: New moderation level
        """
        self.level = level
    
    def moderate(
        self,
        content: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ModerationResult:
        """Moderate content.
        
        Args:
            content: Content to moderate
            context: Optional context information
            
        Returns:
            ModerationResult with moderation details
        """
        self._stats["total_checked"] += 1
        
        if not content:
            return ModerationResult(
                is_approved=False,
                score=0.0,
                violations=[{
                    "type": PolicyViolation.SPAM.value,
                    "severity": "high",
                    "message": "Empty content",
                }],
            )
        
        violations = []
        suggestions = []
        sanitized = content
        score = 1.0
        
        # Apply moderation based on level
        if self.level == ModerationLevel.NONE:
            return ModerationResult(
                is_approved=True,
                score=1.0,
                sanitized_content=content,
            )
        
        # Check profanity
        if self.level in (ModerationLevel.LIGHT, ModerationLevel.STANDARD, ModerationLevel.STRICT):
            profanity_result = self._check_profanity(content)
            if profanity_result:
                violations.extend(profanity_result["violations"])
                sanitized = profanity_result["sanitized"]
                score *= (1 - profanity_result["severity"] * 0.3)
        
        # Check spam patterns
        if self.level in (ModerationLevel.STANDARD, ModerationLevel.STRICT):
            spam_result = self._check_spam(content)
            if spam_result:
                violations.extend(spam_result["violations"])
                suggestions.extend(spam_result["suggestions"])
                score *= (1 - spam_result["severity"] * 0.2)
        
        # Check for competitor mentions
        if self.level == ModerationLevel.STRICT:
            competitor_result = self._check_competitor(content)
            if competitor_result:
                violations.extend(competitor_result["violations"])
                score *= 0.7
        
        # Check unauthorized claims
        if self.level in (ModerationLevel.STANDARD, ModerationLevel.STRICT):
            claims_result = self._check_unauthorized_claims(content)
            if claims_result:
                violations.extend(claims_result["violations"])
                suggestions.extend(claims_result["suggestions"])
                score *= (1 - claims_result["severity"] * 0.3)
        
        # Check custom blocked words
        custom_violations = self._check_custom_words(content)
        if custom_violations:
            violations.extend(custom_violations)
            score *= 0.8
        
        # Check URLs
        url_result = self._check_urls(content)
        if url_result:
            violations.extend(url_result["violations"])
            sanitized = url_result["sanitized"]
        
        # Update statistics
        for v in violations:
            v_type = v.get("type")
            self._stats["violations_by_type"][v_type] = \
                self._stats["violations_by_type"].get(v_type, 0) + 1
        
        if score < 0.3:
            self._stats["total_blocked"] += 1
        elif sanitized != content:
            self._stats["total_modified"] += 1
        
        return ModerationResult(
            is_approved=score >= 0.3,
            score=max(0.0, score),
            violations=violations,
            suggestions=suggestions,
            sanitized_content=sanitized,
            confidence=0.9,
            metadata={
                "original_length": len(content),
                "sanitized_length": len(sanitized),
                "level": self.level.value,
            }
        )
    
    def _check_profanity(self, content: str) -> Optional[Dict[str, Any]]:
        """Check for profanity.
        
        Args:
            content: Content to check
            
        Returns:
            Dictionary with violations and sanitized content
        """
        violations = []
        sanitized = content
        max_severity = 0.0
        
        for pattern in self._profanity_re:
            matches = pattern.findall(content)
            if matches:
                severity = 0.8 if self.level == ModerationLevel.STRICT else 0.6
                max_severity = max(max_severity, severity)
                violations.append({
                    "type": PolicyViolation.PROFANITY.value,
                    "severity": severity,
                    "message": f"Profanity detected",
                    "matches": len(matches),
                })
                
                # Censor in sanitized version
                if self.level in (ModerationLevel.STANDARD, ModerationLevel.STRICT):
                    sanitized = pattern.sub("***", sanitized)
        
        if violations:
            return {
                "violations": violations,
                "sanitized": sanitized,
                "severity": max_severity,
            }
        return None
    
    def _check_spam(self, content: str) -> Optional[Dict[str, Any]]:
        """Check for spam patterns.
        
        Args:
            content: Content to check
            
        Returns:
            Dictionary with violations and suggestions
        """
        violations = []
        suggestions = []
        max_severity = 0.0
        
        for pattern in self._spam_re:
            match = pattern.search(content)
            if match:
                severity = 0.5
                max_severity = max(max_severity, severity)
                violations.append({
                    "type": PolicyViolation.SPAM.value,
                    "severity": severity,
                    "message": f"Spam pattern detected: {match.group()[:50]}",
                })
                suggestions.append("Remove or tone down promotional language")
        
        # Check excessive caps
        caps_ratio = sum(1 for c in content if c.isupper()) / max(1, len(content))
        if caps_ratio > 0.5 and len(content) > 20:
            violations.append({
                "type": PolicyViolation.SPAM.value,
                "severity": 0.3,
                "message": "Excessive use of capital letters",
            })
            suggestions.append("Reduce use of capital letters")
            max_severity = max(max_severity, 0.3)
        
        if violations:
            return {
                "violations": violations,
                "suggestions": suggestions,
                "severity": max_severity,
            }
        return None
    
    def _check_competitor(self, content: str) -> Optional[Dict[str, Any]]:
        """Check for competitor mentions.
        
        Args:
            content: Content to check
            
        Returns:
            Dictionary with violations
        """
        violations = []
        
        matches = self._competitor_re.findall(content)
        if matches:
            violations.append({
                "type": PolicyViolation.COMPETITOR_MENTION.value,
                "severity": 0.7,
                "message": f"Competitor mention detected ({len(matches)} instances)",
                "matches": len(matches),
            })
        
        if violations:
            return {"violations": violations}
        return None
    
    def _check_unauthorized_claims(self, content: str) -> Optional[Dict[str, Any]]:
        """Check for unauthorized claims.
        
        Args:
            content: Content to check
            
        Returns:
            Dictionary with violations and suggestions
        """
        violations = []
        suggestions = []
        
        for pattern in self._unauthorized_claims_re:
            matches = pattern.findall(content)
            if matches:
                violations.append({
                    "type": PolicyViolation.UNAUTHORIZED_CLAIMS.value,
                    "severity": 0.8,
                    "message": f"Unauthorized claim detected",
                })
                suggestions.append(
                    "Use softer language: 'may help' instead of 'treats/cures'. "
                    "Add disclaimer that these are not medical/legally-binding claims."
                )
        
        if violations:
            return {
                "violations": violations,
                "suggestions": suggestions,
                "severity": 0.8,
            }
        return None
    
    def _check_custom_words(self, content: str) -> List[Dict[str, Any]]:
        """Check for custom blocked words.
        
        Args:
            content: Content to check
            
        Returns:
            List of violations
        """
        violations = []
        content_lower = content.lower()
        
        for word in self._custom_blocked_words:
            if word in content_lower:
                violations.append({
                    "type": PolicyViolation.INAPPROPRIATE_CONTENT.value,
                    "severity": 0.6,
                    "message": f"Custom blocked word: {word}",
                })
        
        return violations
    
    def _check_urls(self, content: str) -> Optional[Dict[str, Any]]:
        """Check for URLs.
        
        Args:
            content: Content to check
            
        Returns:
            Dictionary with violations and sanitized content
        """
        url_pattern = re.compile(r'https?://\S+')
        violations = []
        sanitized = content
        
        for match in url_pattern.finditer(content):
            url = match.group()
            
            # Check if URL is blocked
            if url in self._blocked_urls:
                violations.append({
                    "type": PolicyViolation.SPAM.value,
                    "severity": 0.5,
                    "message": f"Blocked URL detected",
                })
                sanitized = sanitized.replace(url, "[link removed]")
            
            # Check if URL is allowed
            elif url not in self._allowed_urls and self.level == ModerationLevel.STRICT:
                # In strict mode, remove unverified URLs
                sanitized = sanitized.replace(url, "[link removed]")
                violations.append({
                    "type": PolicyViolation.SPAM.value,
                    "severity": 0.3,
                    "message": f"URL removed for safety",
                })
        
        if violations:
            return {"violations": violations, "sanitized": sanitized}
        return None
    
    def add_blocked_word(self, word: str) -> None:
        """Add a word to the blocked list.
        
        Args:
            word: Word to block
        """
        self._custom_blocked_words.add(word.lower())
    
    def remove_blocked_word(self, word: str) -> None:
        """Remove a word from the blocked list.
        
        Args:
            word: Word to remove
        """
        self._custom_blocked_words.discard(word.lower())
    
    def add_allowed_url(self, url: str) -> None:
        """Add a URL to the allowed list.
        
        Args:
            url: URL to allow
        """
        self._allowed_urls.add(url)
    
    def add_blocked_url(self, url: str) -> None:
        """Add a URL to the blocked list.
        
        Args:
            url: URL to block
        """
        self._blocked_urls.add(url)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get moderation statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            **self._stats,
            "approval_rate": (
                (self._stats["total_checked"] - self._stats["total_blocked"]) /
                max(1, self._stats["total_checked"])
            ),
            "current_level": self.level.value,
        }
    
    def reset_statistics(self) -> None:
        """Reset moderation statistics."""
        self._stats = {
            "total_checked": 0,
            "total_blocked": 0,
            "total_modified": 0,
            "violations_by_type": {},
        }
