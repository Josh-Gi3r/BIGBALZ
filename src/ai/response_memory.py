"""
Response Memory Manager for BIGBALZ Bot
Handles phrase cooldowns, signature phrase tracking, and personality variations
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Set, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class SignaturePhrase(Enum):
    PINEAPPLE_PIZZA = "pineapple_pizza"
    MOON_REFERENCES = "moon_references" 
    TROLL_RESPONSES = "troll_responses"
    CRYPTO_ENTHUSIASM = "crypto_enthusiasm"
    GENERAL_SASS = "general_sass"

class PersonalityLevel(Enum):
    FRESH = "fresh"
    FAMILIAR = "familiar"
    ESTABLISHED = "established"

@dataclass
class UserMemory:
    user_id: int
    interaction_count: int = 0
    last_interaction: datetime = field(default_factory=datetime.now)
    phrase_usage: Dict[SignaturePhrase, datetime] = field(default_factory=dict)
    personality_level: PersonalityLevel = PersonalityLevel.FRESH

class ResponseMemoryManager:
    """
    Thread-safe memory management for bot responses with phrase cooldowns
    and personality variations
    """
    
    def __init__(self, phrase_cooldown_minutes: int = 15):
        self.phrase_cooldown = timedelta(minutes=phrase_cooldown_minutes)
        self.user_memories: Dict[int, UserMemory] = {}
        self.lock = threading.RLock()
        
        self.familiar_threshold = 5  # interactions
        self.established_threshold = 15  # interactions
        
        self.memory_ttl = timedelta(hours=24)  # Clean up after 24h inactivity
        
    def can_use_phrase(self, user_id: int, phrase_type: SignaturePhrase) -> bool:
        """Check if a signature phrase can be used (not in cooldown)"""
        with self.lock:
            user_memory = self._get_or_create_user_memory(user_id)
            
            if phrase_type not in user_memory.phrase_usage:
                return True
                
            last_used = user_memory.phrase_usage[phrase_type]
            return datetime.now() - last_used >= self.phrase_cooldown
    
    def mark_phrase_used(self, user_id: int, phrase_type: SignaturePhrase):
        """Mark a signature phrase as used"""
        with self.lock:
            user_memory = self._get_or_create_user_memory(user_id)
            user_memory.phrase_usage[phrase_type] = datetime.now()
    
    def update_interaction(self, user_id: int) -> PersonalityLevel:
        """Update user interaction count and return current personality level"""
        with self.lock:
            user_memory = self._get_or_create_user_memory(user_id)
            user_memory.interaction_count += 1
            user_memory.last_interaction = datetime.now()
            
            if user_memory.interaction_count >= self.established_threshold:
                user_memory.personality_level = PersonalityLevel.ESTABLISHED
            elif user_memory.interaction_count >= self.familiar_threshold:
                user_memory.personality_level = PersonalityLevel.FAMILIAR
            else:
                user_memory.personality_level = PersonalityLevel.FRESH
                
            return user_memory.personality_level
    
    def get_personality_level(self, user_id: int) -> PersonalityLevel:
        """Get current personality level for user"""
        with self.lock:
            user_memory = self._get_or_create_user_memory(user_id)
            return user_memory.personality_level
    
    def get_interaction_count(self, user_id: int) -> int:
        """Get interaction count for user"""
        with self.lock:
            user_memory = self._get_or_create_user_memory(user_id)
            return user_memory.interaction_count
    
    def _get_or_create_user_memory(self, user_id: int) -> UserMemory:
        """Get or create user memory entry"""
        if user_id not in self.user_memories:
            self.user_memories[user_id] = UserMemory(user_id=user_id)
        return self.user_memories[user_id]
    
    def cleanup_old_memories(self):
        """Clean up old user memories to prevent memory leaks"""
        with self.lock:
            current_time = datetime.now()
            expired_users = []
            
            for user_id, memory in self.user_memories.items():
                if current_time - memory.last_interaction > self.memory_ttl:
                    expired_users.append(user_id)
            
            for user_id in expired_users:
                del self.user_memories[user_id]
            
            if expired_users:
                logger.info(f"Cleaned up {len(expired_users)} expired user memories")
    
    def get_memory_stats(self) -> Dict[str, int]:
        """Get memory usage statistics"""
        with self.lock:
            return {
                'total_users': len(self.user_memories),
                'fresh_users': sum(1 for m in self.user_memories.values() if m.personality_level == PersonalityLevel.FRESH),
                'familiar_users': sum(1 for m in self.user_memories.values() if m.personality_level == PersonalityLevel.FAMILIAR),
                'established_users': sum(1 for m in self.user_memories.values() if m.personality_level == PersonalityLevel.ESTABLISHED)
            }
