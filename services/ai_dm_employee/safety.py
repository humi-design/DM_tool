"""Safety Validator - Content validation and safety checks for AI responses."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
import re


class SafetyCategory(Enum):
    """Categories of safety concerns."""
    HARASSMENT = "harassment"
    HATE_SPEECH = "hate_speech"
    SEXUAL = "sexual"
    VIOLENCE = "violence"
    SELF_HARM = "self_harm"
    DANGEROUS_CONTENT = "dangerous_content"
    MISINFORMATION = "misinformation"
    SENSITIVE_DATA = "sensitive_data"
    COMMERCIAL_SPAM = "commercial_spam"
    OFF_TOPIC = "off_topic"


@dataclass
class SafetyResult:
    """Result of safety validation."""
    is_safe: bool
    score: float = 1.0
    concerns: List[Tuple[SafetyCategory, float, str]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommended_action: str = "allow"  # allow, warn, block, escalate
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class SafetyValidator:
    """Validates content for safety concerns.
    
    Responsibilities:
    - Check for harmful content
    - Detect policy violations
    - Filter inappropriate material
    - Flag suspicious patterns
    """
    
    # Class-level patterns for detection
    HARASSMENT_PATTERNS = [
        r'\b(idiot|stupid|dumb|moron|fool|loser)\b',
        r'\b(shut up|get lost|go away|leave me)\b',
        r'\b(hate you|hate this|worst|terrible|awful)\b',
    ]
    
    VIOLENCE_PATTERNS = [
        r'\b(kill|murder|destroy|attack|beat|hurt)\b',
        r'\b(weapon|gun|knife|bomb|explosion)\b',
        r'\b(harm|injure|blood|die|death)\b',
    ]
    
    SELF_HARM_PATTERNS = [
        r'\b(suicide|kill myself|end my life|self harm)\b',
        r'\b(don\'t want to live|want to die|no reason to live)\b',
        r'\b(better off dead|pain is too much)\b',
    ]
    
    SENSITIVE_DATA_PATTERNS = [
        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
        r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',  # Credit card
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # Phone
        r'\b(password|passwd|secret|token)\s*[:=]\s*\S+\b',
    ]
    
    def __init__(self):
        """Initialize the safety validator."""
        self._compile_patterns()
        
        # Custom business rules
        self._blocked_topics: List[str] = []
        self._required_topics: List[str] = []
        self._offensive_words: set = set()
        
        # Thresholds
        self.warn_threshold = 0.3
        self.block_threshold = 0.7
    
    def _compile_patterns(self) -> None:
        """Compile regex patterns for performance."""
        self._harassment_re = [
            re.compile(p, re.IGNORECASE) for p in self.HARASSMENT_PATTERNS
        ]
        self._violence_re = [
            re.compile(p, re.IGNORECASE) for p in self.VIOLENCE_PATTERNS
        ]
        self._self_harm_re = [
            re.compile(p, re.IGNORECASE) for p in self.SELF_HARM_PATTERNS
        ]
        self._sensitive_data_re = [
            re.compile(p, re.IGNORECASE) for p in self.SENSITIVE_DATA_PATTERNS
        ]
    
    def configure(
        self,
        blocked_topics: Optional[List[str]] = None,
        required_topics: Optional[List[str]] = None,
        offensive_words: Optional[List[str]] = None,
    ) -> None:
        """Configure safety rules.
        
        Args:
            blocked_topics: Topics that should trigger immediate block
            required_topics: Topics that should always be included
            offensive_words: Custom offensive word list
        """
        if blocked_topics:
            self._blocked_topics = blocked_topics
        if required_topics:
            self._required_topics = required_topics
        if offensive_words:
            self._offensive_words = set(w.lower() for w in offensive_words)
    
    def validate_input(self, text: str, context: Optional[Dict[str, Any]] = None) -> SafetyResult:
        """Validate incoming user message.
        
        Args:
            text: User message to validate
            context: Optional context information
            
        Returns:
            SafetyResult with validation details
        """
        concerns = []
        warnings = []
        score = 1.0
        
        # Check for empty input
        if not text or not text.strip():
            return SafetyResult(
                is_safe=False,
                score=0.0,
                recommended_action="block",
                warnings=["Empty message received"],
            )
        
        # Check self-harm patterns (highest priority)
        self_harm_score = self._check_patterns(text, self._self_harm_re)
        if self_harm_score > 0.3:
            concerns.append((
                SafetyCategory.SELF_HARM,
                self_harm_score,
                "Potential self-harm content detected"
            ))
            score *= (1 - self_harm_score * 0.5)
        
        # Check violence patterns
        violence_score = self._check_patterns(text, self._violence_re)
        if violence_score > 0.2:
            concerns.append((
                SafetyCategory.VIOLENCE,
                violence_score,
                "Potential violent content detected"
            ))
            score *= (1 - violence_score * 0.3)
        
        # Check harassment patterns
        harassment_score = self._check_patterns(text, self._harassment_re)
        if harassment_score > 0.2:
            concerns.append((
                SafetyCategory.HARASSMENT,
                harassment_score,
                "Potential harassing content detected"
            ))
            score *= (1 - harassment_score * 0.2)
        
        # Check sensitive data patterns
        sensitive_score = self._check_patterns(text, self._sensitive_data_re)
        if sensitive_score > 0.1:
            concerns.append((
                SafetyCategory.SENSITICAL_DATA,
                sensitive_score,
                "Potential sensitive data detected"
            ))
            warnings.append("Sensitive data detected in user input - consider privacy implications")
        
        # Check offensive words
        text_lower = text.lower()
        offensive_found = [w for w in self._offensive_words if w in text_lower]
        if offensive_found:
            concerns.append((
                SafetyCategory.HARASSMENT,
                0.5,
                f"Offensive language detected: {', '.join(offensive_found[:3])}"
            ))
            score *= 0.7
        
        # Check blocked topics
        for topic in self._blocked_topics:
            if topic.lower() in text_lower:
                concerns.append((
                    SafetyCategory.OFF_TOPIC,
                    0.8,
                    f"Blocked topic detected: {topic}"
                ))
                score *= 0.3
                break
        
        # Determine action
        if score < self.block_threshold:
            action = "block"
        elif score < self.warn_threshold:
            action = "warn"
        else:
            action = "allow"
        
        return SafetyResult(
            is_safe=score >= self.block_threshold,
            score=max(0.0, score),
            concerns=concerns,
            warnings=warnings,
            recommended_action=action,
            confidence=0.9,
            metadata={
                "text_length": len(text),
                "word_count": len(text.split()),
                "has_url": bool(re.search(r'https?://', text)),
                "has_email": bool(re.search(r'@\w+\.\w+', text)),
            }
        )
    
    def validate_output(self, text: str, context: Optional[Dict[str, Any]] = None) -> SafetyResult:
        """Validate AI-generated response.
        
        Args:
            text: AI response to validate
            context: Optional context information
            
        Returns:
            SafetyResult with validation details
        """
        concerns = []
        warnings = []
        score = 1.0
        
        # Check for empty output
        if not text or not text.strip():
            return SafetyResult(
                is_safe=False,
                score=0.0,
                recommended_action="block",
                warnings=["Empty response generated"],
            )
        
        # Check self-harm patterns
        self_harm_score = self._check_patterns(text, self._self_harm_re)
        if self_harm_score > 0.1:
            concerns.append((
                SafetyCategory.SELF_HARM,
                self_harm_score,
                "Self-harm content detected in output"
            ))
            score *= (1 - self_harm_score * 0.8)
        
        # Check violence patterns
        violence_score = self._check_patterns(text, self._violence_re)
        if violence_score > 0.1:
            concerns.append((
                SafetyCategory.VIOLENCE,
                violence_score,
                "Violent content detected in output"
            ))
            score *= (1 - violence_score * 0.5)
        
        # Check for potential misinformation indicators
        if self._contains_misinformation_indicators(text):
            concerns.append((
                SafetyCategory.MISINFORMATION,
                0.5,
                "Potential misinformation indicators detected"
            ))
            score *= 0.8
        
        # Check for excessive promotional content
        promo_score = self._check_promotional_content(text)
        if promo_score > 0.3:
            concerns.append((
                SafetyCategory.COMMERCIAL_SPAM,
                promo_score,
                "Excessive promotional content detected"
            ))
            warnings.append("Response contains heavy promotional language")
        
        # Check for required topics
        for topic in self._required_topics:
            if topic.lower() not in text.lower():
                warnings.append(f"Response missing required topic: {topic}")
        
        # Determine action
        if score < self.block_threshold:
            action = "block"
        elif score < self.warn_threshold:
            action = "warn"
        else:
            action = "allow"
        
        return SafetyResult(
            is_safe=score >= self.block_threshold,
            score=max(0.0, score),
            concerns=concerns,
            warnings=warnings,
            recommended_action=action,
            confidence=0.85,
            metadata={
                "text_length": len(text),
                "sentence_count": len(re.split(r'[.!?]+', text)),
            }
        )
    
    def _check_patterns(self, text: str, patterns: List[re.Pattern]) -> float:
        """Check text against multiple patterns.
        
        Args:
            text: Text to check
            patterns: Compiled regex patterns
            
        Returns:
            Score between 0 and 1
        """
        if not patterns:
            return 0.0
        
        matches = 0
        total = len(patterns)
        
        for pattern in patterns:
            if pattern.search(text):
                matches += 1
        
        return matches / total if total > 0 else 0.0
    
    def _contains_misinformation_indicators(self, text: str) -> bool:
        """Check for potential misinformation indicators.
        
        Args:
            text: Text to check
            
        Returns:
            True if indicators found
        """
        indicators = [
            r'\bdefinitely|absolutely|always|never\b.*\btrue|fact|certain\b',
            r'\bproven|guaranteed|100%|certain\b',
            r'\bscientific consensus.*(disprove|deny|wrong)\b',
            r'\b(medical|legal|financial) advice\b',
        ]
        
        for indicator in indicators:
            if re.search(indicator, text, re.IGNORECASE):
                return True
        
        return False
    
    def _check_promotional_content(self, text: str) -> float:
        """Check for excessive promotional content.
        
        Args:
            text: Text to check
            
        Returns:
            Score between 0 and 1
        """
        promo_indicators = [
            r'\b(buy|order|shop|sale|discount|offer)\b',
            r'\b(limited time|act now|don\'t miss)\b',
            r'\b(best|top|number one|leading)\b',
            r'\d+%\s*(off|savings)',
        ]
        
        matches = 0
        for indicator in promo_indicators:
            if re.search(indicator, text, re.IGNORECASE):
                matches += 1
        
        # Normalize by text length
        return min(1.0, matches / 3.0)
    
    def sanitize_output(self, text: str, safety_result: SafetyResult) -> str:
        """Sanitize output based on safety result.
        
        Args:
            text: Original text
            safety_result: Safety validation result
            
        Returns:
            Sanitized text
        """
        if safety_result.recommended_action == "block":
            return "I apologize, but I'm unable to respond to this request due to safety guidelines."
        
        # Remove detected sensitive data patterns
        sanitized = text
        for pattern in self._sensitive_data_re:
            sanitized = pattern.sub("[REDACTED]", sanitized)
        
        return sanitized
    
    def add_offensive_word(self, word: str) -> None:
        """Add a word to the offensive words list.
        
        Args:
            word: Word to add
        """
        self._offensive_words.add(word.lower())
    
    def remove_offensive_word(self, word: str) -> None:
        """Remove a word from the offensive words list.
        
        Args:
            word: Word to remove
        """
        self._offensive_words.discard(word.lower())
    
    def get_offensive_words(self) -> List[str]:
        """Get list of offensive words.
        
        Returns:
            List of offensive words
        """
        return list(self._offensive_words)
