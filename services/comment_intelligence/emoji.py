"""Emoji Mapper Module - Processes configurable emoji reactions.

This module handles semantic interpretation of emoji reactions and maps
them to intents and actions using a configurable interpretation layer.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any, Set
import re


class ReactionIntent(Enum):
    """Interpreted intent from emoji reactions."""
    LOVE = "love"
    FIRE = "fire"
    WOW = "wow"
    CLAP = "clap"
    THUMBS_UP = "thumbs_up"
    CELEBRATE = "celebrate"
    EYES = "eyes"
    EMAIL = "email"
    PERFECT = "perfect"
    NEUTRAL = "neutral"


@dataclass
class EmojiMapping:
    """A mapping from emoji(s) to reaction interpretation."""
    emojis: List[str]
    reaction_intent: ReactionIntent
    intent_type: str  # Maps to IntentType
    response_template: str
    priority: int = 0
    conditions: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EmojiReactionResult:
    """Result of processing an emoji reaction."""
    reaction_intent: ReactionIntent
    mapped_intent: str
    response: str
    confidence: float
    emoji_used: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class EmojiMapper:
    """Configurable emoji reaction processor.
    
    This class provides semantic interpretation of emoji reactions
    with configurable mappings and response templates.
    """
    
    DEFAULT_MAPPINGS = [
        # ❤️ Love - Interest/Appreciation
        EmojiMapping(
            emojis=["❤️", "💕", "💖", "💗", "💓", "💞", "💘", "♥️"],
            reaction_intent=ReactionIntent.LOVE,
            intent_type="interest",
            response_template="Thank you so much for the love! ❤️ We really appreciate your support!",
            priority=10
        ),
        
        # 🔥 Fire - Excitement/Interest
        EmojiMapping(
            emojis=["🔥", "🔥", "💯"],
            reaction_intent=ReactionIntent.FIRE,
            intent_type="interest",
            response_template="We're on fire! 🔥 Thanks for the energy!",
            priority=9
        ),
        
        # 😍 Heart Eyes - Strong Interest
        EmojiMapping(
            emojis=["😍", "🥰", "😘", "💝", "💞"],
            reaction_intent=ReactionIntent.LOVE,
            intent_type="interest",
            response_template="You made our day! 😍 Thank you!",
            priority=10
        ),
        
        # 👏 Clapping - Appreciation/Support
        EmojiMapping(
            emojis=["👏", "🙌", "🙏"],
            reaction_intent=ReactionIntent.CLAP,
            intent_type="general",
            response_template="We appreciate you! 🙌 Thanks for the support!",
            priority=8
        ),
        
        # 👍 Thumbs Up - Approval/Interest
        EmojiMapping(
            emojis=["👍", "👌", "✅", "✔️"],
            reaction_intent=ReactionIntent.THUMBS_UP,
            intent_type="interest",
            response_template="Thanks! 👍 We appreciate the thumbs up!",
            priority=7
        ),
        
        # 🙌 Celebration - Celebration/Support
        EmojiMapping(
            emojis=["🙌", "🎉", "🎊", "✨", "💫"],
            reaction_intent=ReactionIntent.CELEBRATE,
            intent_type="general",
            response_template="Celebrating with you! 🙌🎉",
            priority=8
        ),
        
        # 👀 Eyes - Curiosity/Interest
        EmojiMapping(
            emojis=["👀", "🤔", "🧐"],
            reaction_intent=ReactionIntent.EYES,
            intent_type="question",
            response_template="Great observation! 👀 Let us know if you have questions!",
            priority=6
        ),
        
        # 📩 Email/Inbox - Request for info
        EmojiMapping(
            emojis=["📩", "📧", "💌", "📬", "📫"],
            reaction_intent=ReactionIntent.EMAIL,
            intent_type="resource",
            response_template="Got it! 📩 We'll send you the info shortly!",
            priority=9
        ),
        
        # 💯 Hundred - Agreement/Interest
        EmojiMapping(
            emojis=["💯", "💪", "🏆", "🥇"],
            reaction_intent=ReactionIntent.PERFECT,
            intent_type="interest",
            response_template="100% agree! 💯 Thanks for the support!",
            priority=7
        ),
    ]
    
    def __init__(self, mappings: Optional[List[EmojiMapping]] = None):
        """Initialize the emoji mapper.
        
        Args:
            mappings: Optional custom emoji mappings. Uses defaults if not provided.
        """
        self._mappings: List[EmojiMapping] = mappings or self.DEFAULT_MAPPINGS.copy()
        self._emoji_index: Dict[str, EmojiMapping] = {}
        self._build_index()
    
    def _build_index(self) -> None:
        """Build emoji-to-mapping index for fast lookup."""
        self._emoji_index = {}
        for mapping in self._mappings:
            for emoji in mapping.emojis:
                self._emoji_index[emoji] = mapping
    
    def add_mapping(self, mapping: EmojiMapping) -> None:
        """Add a custom emoji mapping.
        
        Args:
            mapping: EmojiMapping to add
        """
        self._mappings.append(mapping)
        for emoji in mapping.emojis:
            self._emoji_index[emoji] = mapping
    
    def remove_mapping(self, reaction_intent: ReactionIntent) -> bool:
        """Remove a mapping by reaction intent.
        
        Args:
            reaction_intent: ReactionIntent to remove
            
        Returns:
            True if removed, False if not found
        """
        original_count = len(self._mappings)
        self._mappings = [m for m in self._mappings if m.reaction_intent != reaction_intent]
        
        if len(self._mappings) < original_count:
            self._build_index()
            return True
        return False
    
    def get_mapping(self, emoji: str) -> Optional[EmojiMapping]:
        """Get mapping for a specific emoji.
        
        Args:
            emoji: The emoji to look up
            
        Returns:
            EmojiMapping if found, None otherwise
        """
        return self._emoji_index.get(emoji)
    
    def process_reaction(
        self,
        emoji: str,
        context: Optional[Dict[str, Any]] = None
    ) -> EmojiReactionResult:
        """Process a single emoji reaction.
        
        Args:
            emoji: The emoji to process
            context: Optional context for personalized responses
            
        Returns:
            EmojiReactionResult with interpretation and response
        """
        context = context or {}
        mapping = self._emoji_index.get(emoji)
        
        if not mapping:
            return EmojiReactionResult(
                reaction_intent=ReactionIntent.NEUTRAL,
                mapped_intent="other",
                response="",
                confidence=0.0,
                emoji_used=emoji,
                metadata={"mapped": False}
            )
        
        # Personalize response if context available
        response = mapping.response_template
        if context.get("author_username"):
            response = response.replace("!", f", @{context['author_username']}!")
        
        return EmojiReactionResult(
            reaction_intent=mapping.reaction_intent,
            mapped_intent=mapping.intent_type,
            response=response,
            confidence=0.9,
            emoji_used=emoji,
            metadata={
                "mapped": True,
                "priority": mapping.priority
            }
        )
    
    def process_reactions(
        self,
        emojis: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> List[EmojiReactionResult]:
        """Process multiple emoji reactions.
        
        Args:
            emojis: List of emojis to process
            context: Optional context for personalized responses
            
        Returns:
            List of EmojiReactionResult for each emoji
        """
        results = []
        seen_intents: Set[ReactionIntent] = set()
        
        for emoji in emojis:
            result = self.process_reaction(emoji, context)
            
            # Deduplicate by reaction intent, keeping highest priority
            if result.reaction_intent not in seen_intents:
                results.append(result)
                seen_intents.add(result.reaction_intent)
            elif result.confidence > 0:
                # Update if this one has higher confidence
                existing_idx = next(
                    i for i, r in enumerate(results) 
                    if r.reaction_intent == result.reaction_intent
                )
                if result.confidence > results[existing_idx].confidence:
                    results[existing_idx] = result
        
        return results
    
    def extract_emojis(self, text: str) -> List[str]:
        """Extract emoji characters from text.
        
        Args:
            text: Text containing emojis
            
        Returns:
            List of extracted emojis
        """
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"  # dingbats
            "\U000024C2-\U0001F251"  # enclosed characters
            "]+", 
            flags=re.UNICODE
        )
        return emoji_pattern.findall(text)
    
    def has_emoji(self, text: str) -> bool:
        """Check if text contains any emoji.
        
        Args:
            text: Text to check
            
        Returns:
            True if text contains emoji, False otherwise
        """
        return bool(self.extract_emojis(text))
    
    def generate_combined_response(
        self,
        reactions: List[EmojiReactionResult],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a combined response for multiple reactions.
        
        Args:
            reactions: List of EmojiReactionResult
            context: Optional context for personalization
            
        Returns:
            Combined response string
        """
        if not reactions:
            return ""
        
        # Sort by priority/confidence
        sorted_reactions = sorted(
            reactions, 
            key=lambda r: r.metadata.get("priority", 0), 
            reverse=True
        )
        
        # Take top responses
        top_reactions = sorted_reactions[:2]
        
        # Combine responses
        responses = [r.response for r in top_reactions if r.response]
        
        if not responses:
            return "Thanks for the reaction! 🙏"
        
        # Join with appropriate connector
        if len(responses) == 1:
            return responses[0]
        else:
            return f"{responses[0]} {responses[1]}"
    
    def get_supported_emojis(self) -> List[str]:
        """Get list of all supported emojis.
        
        Returns:
            List of supported emoji characters
        """
        return list(self._emoji_index.keys())
    
    def get_mappings_by_intent(self, intent: str) -> List[EmojiMapping]:
        """Get all mappings for a specific intent type.
        
        Args:
            intent: Intent type to filter by
            
        Returns:
            List of EmojiMapping for the intent
        """
        return [m for m in self._mappings if m.intent_type == intent]
    
    def export_mappings(self) -> List[Dict[str, Any]]:
        """Export current mappings as dictionaries.
        
        Returns:
            List of mapping dictionaries
        """
        return [
            {
                "emojis": m.emojis,
                "reaction_intent": m.reaction_intent.value,
                "intent_type": m.intent_type,
                "response_template": m.response_template,
                "priority": m.priority,
            }
            for m in self._mappings
        ]
    
    def import_mappings(self, mappings_data: List[Dict[str, Any]]) -> int:
        """Import mappings from dictionaries.
        
        Args:
            mappings_data: List of mapping dictionaries
            
        Returns:
            Number of mappings imported
        """
        count = 0
        for data in mappings_data:
            try:
                mapping = EmojiMapping(
                    emojis=data["emojis"],
                    reaction_intent=ReactionIntent(data["reaction_intent"]),
                    intent_type=data["intent_type"],
                    response_template=data["response_template"],
                    priority=data.get("priority", 0),
                )
                self.add_mapping(mapping)
                count += 1
            except (KeyError, ValueError):
                continue
        
        return count