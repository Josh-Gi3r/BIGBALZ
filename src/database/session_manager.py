"""
Session Manager for BIGBALZ Bot
Handles user session state with automatic TTL cleanup
"""

import time
import logging
import asyncio
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    """
    User session state data
    Stores current token info and interaction state
    """
    chat_id: int
    user_id: int
    current_token: Optional[str] = None  # Token name and symbol
    current_contract: Optional[str] = None
    current_network: Optional[str] = None
    token_data: Optional[Dict[str, Any]] = None
    last_interaction: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)
    
    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if session has expired"""
        return (time.time() - self.last_interaction) > ttl_seconds
    
    def update_interaction(self):
        """Update last interaction time"""
        self.last_interaction = time.time()


class SessionManager:
    """
    Manages user sessions with automatic cleanup
    Thread-safe implementation for concurrent access
    """
    
    def __init__(self, ttl_minutes: int = 30, max_sessions: int = 10000):
        """
        Initialize session manager
        
        Args:
            ttl_minutes: Session timeout in minutes (default: 30)
            max_sessions: Maximum number of concurrent sessions
        """
        self.sessions: Dict[str, SessionState] = {}
        self.ttl_seconds = ttl_minutes * 60
        self.max_sessions = max_sessions
        self._lock = Lock()
        self._cleanup_task = None
        
        logger.info(f"Session manager initialized with {ttl_minutes}min TTL")
    
    def _get_session_key(self, chat_id: int, user_id: int) -> str:
        """Generate unique session key"""
        return f"{chat_id}_{user_id}"
    
    def create_session(self, chat_id: int, user_id: int,
                      token_name: str, contract: str, network: str,
                      token_data: Dict[str, Any]) -> SessionState:
        """
        Create or update session with new token data
        
        Args:
            chat_id: Telegram chat ID
            user_id: Telegram user ID
            token_name: Token name and symbol
            contract: Contract address
            network: Network identifier
            token_data: Complete token data from API
            
        Returns:
            Created or updated SessionState
        """
        session_key = self._get_session_key(chat_id, user_id)
        
        with self._lock:
            # Check if we need to cleanup old sessions
            if len(self.sessions) >= self.max_sessions:
                self._cleanup_oldest_sessions()
            
            # Create or update session
            session = SessionState(
                chat_id=chat_id,
                user_id=user_id,
                current_token=token_name,
                current_contract=contract,
                current_network=network,
                token_data=token_data
            )
            
            self.sessions[session_key] = session
            
            logger.info(f"Session created/updated for user {user_id}: {token_name}")
            return session
    
    def get_session(self, chat_id: int, user_id: int) -> Optional[SessionState]:
        """
        Get current session if valid
        
        Args:
            chat_id: Telegram chat ID
            user_id: Telegram user ID
            
        Returns:
            SessionState if valid, None if expired or not found
        """
        session_key = self._get_session_key(chat_id, user_id)
        
        with self._lock:
            session = self.sessions.get(session_key)
            
            if session:
                if session.is_expired(self.ttl_seconds):
                    # Clean up expired session
                    del self.sessions[session_key]
                    logger.info(f"Session expired for user {user_id}")
                    return None
                else:
                    # Update interaction time
                    session.update_interaction()
                    return session
            
            return None
    
    def update_token_data(self, chat_id: int, user_id: int, 
                         token_data: Dict[str, Any]) -> bool:
        """
        Update token data in existing session
        
        Args:
            chat_id: Telegram chat ID
            user_id: Telegram user ID
            token_data: Updated token data
            
        Returns:
            True if updated, False if session not found
        """
        session_key = self._get_session_key(chat_id, user_id)
        
        with self._lock:
            session = self.sessions.get(session_key)
            if session and not session.is_expired(self.ttl_seconds):
                session.token_data = token_data
                session.update_interaction()
                logger.debug(f"Updated token data for user {user_id}")
                return True
            elif session and session.is_expired(self.ttl_seconds):
                # Clean up expired session
                del self.sessions[session_key]
                logger.info(f"Session expired for user {user_id}")
        
        return False
    
    def delete_session(self, chat_id: int, user_id: int) -> bool:
        """
        Delete a user's session
        
        Args:
            chat_id: Telegram chat ID
            user_id: Telegram user ID
            
        Returns:
            True if deleted, False if not found
        """
        session_key = self._get_session_key(chat_id, user_id)
        
        with self._lock:
            if session_key in self.sessions:
                del self.sessions[session_key]
                logger.info(f"Session deleted for user {user_id}")
                return True
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """
        Remove all expired sessions
        
        Returns:
            Number of sessions cleaned up
        """
        current_time = time.time()
        expired_keys = []
        
        with self._lock:
            for key, session in self.sessions.items():
                if session.is_expired(self.ttl_seconds):
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.sessions[key]
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired sessions")
        
        return len(expired_keys)
    
    def _cleanup_oldest_sessions(self):
        """Remove oldest sessions when hitting max limit"""
        # Sort sessions by last interaction time
        sorted_sessions = sorted(
            self.sessions.items(),
            key=lambda x: x[1].last_interaction
        )
        
        # Remove oldest 10% of sessions
        to_remove = max(1, len(sorted_sessions) // 10)
        
        for key, _ in sorted_sessions[:to_remove]:
            del self.sessions[key]
        
        logger.warning(f"Removed {to_remove} oldest sessions due to limit")
    
    async def start_cleanup_task(self):
        """Start background cleanup task"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            logger.info("Started session cleanup task")
    
    async def stop_cleanup_task(self):
        """Stop background cleanup task"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("Stopped session cleanup task")
    
    async def _periodic_cleanup(self):
        """Periodically clean up expired sessions"""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                cleaned = self.cleanup_expired_sessions()
                
                # Log current session count
                with self._lock:
                    active_count = len(self.sessions)
                
                logger.info(f"Active sessions: {active_count}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
    
    def get_active_session_count(self) -> int:
        """Get number of active sessions"""
        with self._lock:
            return len(self.sessions)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        with self._lock:
            active_sessions = len(self.sessions)
            
            if not self.sessions:
                return {
                    'active_sessions': 0,
                    'oldest_session_age': 0,
                    'newest_session_age': 0,
                    'average_age': 0
                }
            
            current_time = time.time()
            ages = [current_time - s.created_at for s in self.sessions.values()]
            
            return {
                'active_sessions': active_sessions,
                'oldest_session_age': max(ages),
                'newest_session_age': min(ages),
                'average_age': sum(ages) / len(ages),
                'ttl_minutes': self.ttl_seconds / 60
            }
    
    def clear_all_sessions(self):
        """Clear all sessions (use with caution)"""
        with self._lock:
            count = len(self.sessions)
            self.sessions.clear()
            logger.warning(f"Cleared all {count} sessions")
    
    def get_user_sessions(self, user_id: int) -> Dict[int, SessionState]:
        """
        Get all sessions for a specific user across different chats
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Dict mapping chat_id to SessionState
        """
        user_sessions = {}
        
        with self._lock:
            for key, session in self.sessions.items():
                if session.user_id == user_id:
                    user_sessions[session.chat_id] = session
        
        return user_sessions
