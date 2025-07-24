"""
Response Memory System for BIGBALZ Bot
Tracks recent responses to reduce repetitiveness while maintaining personality
"""

import time
import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from threading import Lock
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


@dataclass
class ResponseMemory:
    """Tracks recent responses and phrases used"""
    recent_phrases: deque = field(default_factory=lambda: deque(maxlen=50))
    phrase_cooldowns: Dict[str, float] = field(default_factory=dict)
    response_patterns: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    last_personality_mode: Optional[str] = None
    interaction_count: int = 0
    created_at: float = field(default_factory=time.time)


class ResponseMemoryManager:
    """
    Manages response memory to reduce repetitiveness
    Tracks phrases, patterns, and personality modes per user
    """
    
    def __init__(self, phrase_cooldown_minutes: int = 15):
        """
        Initialize response memory manager
        
        Args:
            phrase_cooldown_minutes: Minutes before a phrase can be reused
        """
        self.user_memories: Dict[int, ResponseMemory] = {}
        self.phrase_cooldown_seconds = phrase_cooldown_minutes * 60
        self._lock = Lock()
        
        self.signature_phrases = {
            'pineapple_pizza': [
                'pineapple on pizza',
                'pineapple pizza',
                'war crime',
                'fucking kidding me'
            ],
            'moon_references': [
                'to the moon',
                'moon energy',
                'moonshot',
                'lambo',
                'wagmi',
                'lfg'
            ],
            'casino_gambling': [
                'casino',
                'house always wins',
                'welcome to the casino',
                'gambling addiction'
            ],
            'harsh_reality': [
                'enjoy poverty',
                'see you at mcdonalds',
                'hope you like ramen',
                'financial natural selection'
            ],
            'troll_responses': [
                'savage comeback',
                'roast',
                'clap back',
                'witty insult',
                'sassy response',
                'burn',
                'comeback',
                'savage',
                'destroyed',
                'obliterated'
            ]
        }
        
        logger.info(f"Response memory manager initialized with {phrase_cooldown_minutes}min cooldowns")
    
    def should_use_phrase(self, user_id: int, phrase: str, category: str = None) -> bool:
        """
        Check if a phrase should be used based on recent usage
        
        Args:
            user_id: User ID
            phrase: Phrase to check
            category: Optional category for signature phrases
            
        Returns:
            True if phrase can be used, False if on cooldown
        """
        with self._lock:
            memory = self._get_user_memory(user_id)
            
            phrase_lower = phrase.lower()
            last_used = memory.phrase_cooldowns.get(phrase_lower, 0)
            
            if time.time() - last_used < self.phrase_cooldown_seconds:
                logger.debug(f"Phrase '{phrase}' on cooldown for user {user_id}")
                return False
            
            if category and category in self.signature_phrases:
                for sig_phrase in self.signature_phrases[category]:
                    if sig_phrase in memory.phrase_cooldowns:
                        last_used = memory.phrase_cooldowns[sig_phrase]
                        if time.time() - last_used < self.phrase_cooldown_seconds:
                            logger.debug(f"Category '{category}' on cooldown for user {user_id}")
                            return False
            
            return True
    
    def record_phrase_usage(self, user_id: int, phrase: str, category: str = None):
        """
        Record that a phrase was used
        
        Args:
            user_id: User ID
            phrase: Phrase that was used
            category: Optional category for signature phrases
        """
        with self._lock:
            memory = self._get_user_memory(user_id)
            current_time = time.time()
            
            phrase_lower = phrase.lower()
            memory.phrase_cooldowns[phrase_lower] = current_time
            memory.recent_phrases.append((phrase_lower, current_time))
            
            if category and category in self.signature_phrases:
                for sig_phrase in self.signature_phrases[category]:
                    if sig_phrase in phrase_lower:
                        memory.phrase_cooldowns[sig_phrase] = current_time
            
            logger.debug(f"Recorded phrase usage for user {user_id}: {phrase}")
    
    def get_response_variation_context(self, user_id: int) -> Dict[str, any]:
        """
        Get context for varying responses based on user history
        
        Args:
            user_id: User ID
            
        Returns:
            Context dict with variation suggestions
        """
        with self._lock:
            memory = self._get_user_memory(user_id)
            memory.interaction_count += 1
            
            if memory.interaction_count <= 2:
                personality_mode = "fresh"
            elif memory.interaction_count <= 5:
                personality_mode = "familiar"
            else:
                personality_mode = "established"
            
            available_phrases = {}
            current_time = time.time()
            
            for category, phrases in self.signature_phrases.items():
                available_phrases[category] = []
                for phrase in phrases:
                    phrase_lower = phrase.lower()
                    last_used = memory.phrase_cooldowns.get(phrase_lower, 0)
                    
                    if current_time - last_used >= self.phrase_cooldown_seconds:
                        category_available = True
                        if category in self.signature_phrases:
                            for sig_phrase in self.signature_phrases[category]:
                                if sig_phrase in memory.phrase_cooldowns:
                                    sig_last_used = memory.phrase_cooldowns[sig_phrase]
                                    if current_time - sig_last_used < self.phrase_cooldown_seconds:
                                        category_available = False
                                        break
                        
                        if category_available:
                            available_phrases[category].append(phrase)
            
            recent_patterns = dict(memory.response_patterns)
            
            context = {
                'personality_mode': personality_mode,
                'interaction_count': memory.interaction_count,
                'available_signature_phrases': available_phrases,
                'recent_patterns': recent_patterns,
                'last_personality_mode': memory.last_personality_mode
            }
            
            memory.last_personality_mode = personality_mode
            return context
    
    def record_response_pattern(self, user_id: int, pattern_type: str):
        """
        Record a response pattern to track variety
        
        Args:
            user_id: User ID
            pattern_type: Type of response pattern (e.g., 'sarcastic', 'excited', 'dismissive')
        """
        with self._lock:
            memory = self._get_user_memory(user_id)
            memory.response_patterns[pattern_type] += 1
    
    def suggest_personality_variation(self, user_id: int, base_personality: str) -> str:
        """
        Suggest personality variation based on interaction history
        
        Args:
            user_id: User ID
            base_personality: Base personality from BALZ classification
            
        Returns:
            Modified personality suggestion
        """
        context = self.get_response_variation_context(user_id)
        
        if context['personality_mode'] == 'fresh':
            if 'excited' not in context['recent_patterns'] or context['recent_patterns']['excited'] < 2:
                return f"{base_personality} Be extra engaging since this is an early interaction."
        
        elif context['personality_mode'] == 'familiar':
            most_used_pattern = max(context['recent_patterns'].items(), key=lambda x: x[1], default=(None, 0))
            if most_used_pattern[1] > 2:
                return f"{base_personality} Avoid being too {most_used_pattern[0]} since you've used that pattern recently."
        
        else:  # established
            return f"{base_personality} This user knows you well, so be more subtle and avoid your usual catchphrases unless they fit perfectly."
        
        return base_personality
    
    def _get_user_memory(self, user_id: int) -> ResponseMemory:
        """Get or create user memory"""
        if user_id not in self.user_memories:
            self.user_memories[user_id] = ResponseMemory()
        return self.user_memories[user_id]
    
    def cleanup_old_memories(self):
        """Clean up old user memories"""
        current_time = time.time()
        expired_users = []
        
        with self._lock:
            for user_id, memory in self.user_memories.items():
                if current_time - memory.created_at > 86400:
                    expired_users.append(user_id)
        
        for user_id in expired_users:
            del self.user_memories[user_id]
        
        if expired_users:
            logger.info(f"Cleaned up {len(expired_users)} old response memories")
    
    def get_memory_stats(self) -> Dict[str, any]:
        """Get memory statistics"""
        with self._lock:
            return {
                'active_users': len(self.user_memories),
                'total_interactions': sum(m.interaction_count for m in self.user_memories.values()),
                'cooldown_minutes': self.phrase_cooldown_seconds / 60
            }
