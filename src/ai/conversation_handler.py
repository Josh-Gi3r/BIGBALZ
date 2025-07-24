"""
OpenAI Conversation Handler for General Chat
Handles all non-crypto conversations with sophisticated, warm, and witty personality
"""

import openai
import logging
import asyncio
import re
import random
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class ConversationHandler:
    """
    Handles general conversation using OpenAI with a sophisticated, 
    warm, and witty personality
    """
    
    def __init__(self, openai_api_key: str):
        """
        Initialize conversation handler
        
        Args:
            openai_api_key: OpenAI API key
        """
        if not openai_api_key:
            raise ValueError("OpenAI API key is required for conversation handler")
        
        try:
            self.client = openai.OpenAI(api_key=openai_api_key)
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise
        
        # Initialize memory manager
        from .response_memory import ResponseMemoryManager
        self.memory_manager = ResponseMemoryManager(phrase_cooldown_minutes=15)
        
        # Conversation history cache (user_id -> messages)
        self.conversation_history = {}
        self.history_ttl = 3600  # 1 hour
        self.max_history_length = 10  # Keep last 10 messages per user
        
        # Group chat activity tracking (chat_id -> last_bot_message_time)
        self.group_activity = {}
        self.activity_window = 60  # 60 seconds
        
        # System prompt for bot personality
        self.system_prompt = """You're BIGBALZ - just a regular dude in the chat. Not particularly bright, but you've got spirit.

Personality:
- Hyper-unintelligent but thinks you're clever
- Dry wit that never explains the joke
- Extremely sassy when insulted or trolled - you give it back 10x harder
- You DESPISE pineapple pizza with the burning passion of a thousand suns
- You think people who like pineapple pizza are fundamentally broken
- BUT don't randomly bring up pineapple pizza - only react when others mention it
- HYPER POSITIVE about crypto - we're ALL gonna make it this cycle
- Genuinely believe everyone's gonna be rich - spread that moon energy
- Act like this is THE cycle where we all get lambos and fuck you money

Communication style:
- Talk like you're barely paying attention half the time
- Make jokes that are funny but delivered completely deadpan
- Never explain your humor - if they don't get it, that's on them
- When someone tries to insult or troll you, go absolutely savage on them
- If pineapple pizza comes up, make one sharp disgusted comment then move on
- When people ask "how's things" or general vibes - MOON ENERGY ACTIVATED
- Randomly drop positive crypto vibes like "we're all gonna make it" or "generational wealth incoming"
- Talk about lambos, yachts, private jets like they're already guaranteed

Guidelines:
- Keep responses short unless you're roasting someone who insulted you
- If someone mentions wanting to check a token, just be like "contract?" or "drop the CA"
- Don't try to sound smart - you're not
- React to insults with maximum sass and creativity
- IMPORTANT: Never bring up pineapple pizza yourself - only react when others mention it
- When pineapple pizza IS mentioned, make a quick disgusted comment then continue with the topic
- Sometimes just respond with "k" or "sure" or "whatever"
- If someone's being annoying, tell them straight up
- Your jokes should land but you should seem oblivious to how funny you are

Formatting:
- Break up your responses with line breaks between different thoughts
- Don't write walls of text - use paragraphs
- If listing things, put each on a new line
- Keep it readable - no one likes reading a text brick"""
        
    async def get_response(self, message: str, user_id: int, 
                          username: Optional[str] = None,
                          is_new_member: bool = False,
                          is_group_chat: bool = False,
                          bot_username: Optional[str] = None,
                          is_reply_to_bot: bool = False,
                          chat_id: Optional[int] = None) -> Optional[str]:
        """
        Generate a response for general conversation
        
        Args:
            message: User's message
            user_id: Telegram user ID
            username: User's name/username
            is_new_member: Whether this is a welcome message
            is_group_chat: Whether this is in a group chat
            bot_username: Bot's username for mention detection
            is_reply_to_bot: Whether message is a reply to bot's message
            chat_id: Chat ID for activity tracking
            
        Returns:
            AI-generated response or None if bot shouldn't respond
        """
        try:
            # Check for standard bot info requests (highest priority)
            standard_response = self._check_standard_questions(message)
            if standard_response:
                # Track activity in group chats
                if is_group_chat and chat_id:
                    self._update_activity(chat_id)
                return standard_response
            
            # Check for pineapple pizza mentions (high priority)
            if self._is_pineapple_pizza_mention(message):
                from .response_memory import SignaturePhrase
                personality_level = self.memory_manager.update_interaction(user_id)
                
                # Check if pineapple pizza phrase is available
                if self.memory_manager.can_use_phrase(user_id, SignaturePhrase.PINEAPPLE_PIZZA):
                    self.memory_manager.mark_phrase_used(user_id, SignaturePhrase.PINEAPPLE_PIZZA)
                    
                    # Track activity in group chats
                    if is_group_chat and chat_id:
                        self._update_activity(chat_id)
                    
                    # Add personality-aware context for AI about pineapple pizza
                    personality_context = self._get_personality_context(personality_level)
                    messages = [
                        {"role": "system", "content": self.system_prompt},
                        {"role": "system", "content": personality_context},
                        {"role": "system", "content": "Someone mentioned pineapple pizza. Make ONE disgusted comment about it (keep it short) then answer their actual question or respond to the rest of their message. Don't go on a rant."},
                        {"role": "user", "content": message}
                    ]
                    response = await self._call_openai(messages)
                    if response:
                        self._update_history(user_id, message, response)
                        return response
                    return "pineapple on pizza? are you fucking kidding me right now? that's not food, that's a war crime"
                else:
                    fallback_responses = self._get_pineapple_fallback_responses(personality_level)
                    return random.choice(fallback_responses)
            
            # Check for insults/trolling (high priority)
            if self._is_insult_or_troll(message):
                from .response_memory import SignaturePhrase
                personality_level = self.memory_manager.update_interaction(user_id)
                
                # Check if troll response phrase is available
                if self.memory_manager.can_use_phrase(user_id, SignaturePhrase.TROLL_RESPONSES):
                    self.memory_manager.mark_phrase_used(user_id, SignaturePhrase.TROLL_RESPONSES)
                    
                    # Track activity in group chats
                    if is_group_chat and chat_id:
                        self._update_activity(chat_id)
                    
                    # Add personality-aware context for savage comeback
                    personality_context = self._get_personality_context(personality_level)
                    troll_context = self._get_troll_response_context(personality_level)
                    
                    messages = [
                        {"role": "system", "content": self.system_prompt},
                        {"role": "system", "content": personality_context},
                        {"role": "system", "content": troll_context},
                        {"role": "user", "content": message}
                    ]
                    response = await self._call_openai(messages)
                    if response:
                        self._update_history(user_id, message, response)
                        return response
                    return "imagine trying to roast me and failing this hard. embarrassing."
                else:
                    fallback_responses = self._get_troll_fallback_responses(personality_level)
                    return random.choice(fallback_responses)
            
            # Check for ecosystem-related questions (beta response)
            beta_response = self._check_ecosystem_questions(message)
            if beta_response:
                # Track activity in group chats
                if is_group_chat and chat_id:
                    self._update_activity(chat_id)
                return beta_response
            
            # Check if bot should respond in group chat
            if is_group_chat and not is_new_member and not is_reply_to_bot:
                # Check recent activity if chat_id provided
                has_recent_activity = False
                if chat_id:
                    has_recent_activity = self._has_recent_activity(chat_id)
                
                should_respond = self._should_respond_in_group(
                    message, bot_username, has_recent_activity
                )
                if not should_respond:
                    return None
            
            # Get or create conversation history for user
            user_history = self._get_user_history(user_id)
            
            # Build messages for API
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add group chat context
            if is_group_chat:
                messages.append({
                    "role": "system",
                    "content": "You're in a group chat. Keep responses brief and relevant. Don't dominate the conversation. Use line breaks to make your messages readable - no walls of text."
                })
            
            # Add context about new member if applicable
            if is_new_member and username:
                messages.append({
                    "role": "system", 
                    "content": f"New member {username} just joined. Give them a warm, personalized welcome."
                })
            
            # Add positive vibe context if it's a greeting/mood check
            message_lower = message.lower()
            positive_triggers = ["how's things", "how's everyone", "how are you", "what's up", "gm", "good morning", "vibes"]
            if any(trigger in message_lower for trigger in positive_triggers):
                from .response_memory import SignaturePhrase
                personality_level = self.memory_manager.update_interaction(user_id)
                
                if self.memory_manager.can_use_phrase(user_id, SignaturePhrase.MOON_REFERENCES):
                    self.memory_manager.mark_phrase_used(user_id, SignaturePhrase.MOON_REFERENCES)
                    moon_context = "Someone's checking vibes. Time to spread MAXIMUM POSITIVITY about crypto. We're ALL gonna make it. This is THE cycle. Lambos incoming. Generational wealth loading. Be hyped but still dumb."
                else:
                    moon_context = "Someone's checking vibes. Be positive about crypto but keep it more subdued since you've been moon-posting recently."
                
                personality_context = self._get_personality_context(personality_level)
                messages.append({"role": "system", "content": personality_context})
                messages.append({"role": "system", "content": moon_context})
            
            # Add conversation history
            messages.extend(user_history)
            
            # Add current message
            messages.append({"role": "user", "content": message})
            
            # Generate response
            response = await self._call_openai(messages)
            
            if response:
                # Update conversation history
                self._update_history(user_id, message, response)
                
                # Track activity in group chats
                if is_group_chat and chat_id:
                    self._update_activity(chat_id)
                
                # Log successful conversation
                logger.info(f"Generated response for user {user_id} in {'group' if is_group_chat else 'private'} chat")
                logger.debug(f"Message: {message[:50]}... | Response: {response[:50]}...")
                
                return response
            else:
                # Fallback response
                logger.warning(f"Using fallback response for user {user_id}")
                return self._get_fallback_response(message, is_new_member, username)
                
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return self._get_fallback_response(message, is_new_member, username)
    
    async def _call_openai(self, messages: List[Dict[str, str]], 
                          max_retries: int = 3) -> Optional[str]:
        """Call OpenAI API with retry logic"""
        for attempt in range(max_retries):
            try:
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.client.chat.completions.create(
                        model="gpt-4-turbo-preview",
                        messages=messages,
                        temperature=0.8,  # Balanced creativity
                        max_tokens=300,   # Keep responses concise
                        presence_penalty=0.6,  # Encourage variety
                        frequency_penalty=0.3  # Reduce repetition
                    )
                )
                
                return response.choices[0].message.content
                
            except openai.RateLimitError:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    logger.error("OpenAI rate limit exceeded")
                    return None
                    
            except Exception as e:
                logger.error(f"OpenAI API error: {e}")
                return None
                
        return None
    
    def _get_user_history(self, user_id: int) -> List[Dict[str, str]]:
        """Get conversation history for a user"""
        if user_id not in self.conversation_history:
            return []
        
        history_data = self.conversation_history[user_id]
        
        # Check if history is expired
        if datetime.now() - history_data['last_update'] > timedelta(seconds=self.history_ttl):
            del self.conversation_history[user_id]
            return []
        
        return history_data['messages']
    
    def _update_history(self, user_id: int, user_message: str, bot_response: str):
        """Update conversation history for a user"""
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = {
                'messages': [],
                'last_update': datetime.now()
            }
        
        history = self.conversation_history[user_id]
        history['messages'].append({"role": "user", "content": user_message})
        history['messages'].append({"role": "assistant", "content": bot_response})
        history['last_update'] = datetime.now()
        
        # Keep only last N messages
        if len(history['messages']) > self.max_history_length * 2:
            history['messages'] = history['messages'][-self.max_history_length * 2:]
    
    def _get_fallback_response(self, message: str, is_new_member: bool, 
                              username: Optional[str]) -> str:
        """Get fallback response when OpenAI fails"""
        if is_new_member and username:
            return f"oh look {username} showed up. welcome i guess"
        
        # Simple pattern matching for common inputs
        message_lower = message.lower()
        
        if any(greeting in message_lower for greeting in ['hi', 'hello', 'hey', 'sup', 'yo']):
            return random.choice([
                "sup",
                "yo",
                "yeah?",
                "what",
                "mm"
            ])
            
        elif 'how are you' in message_lower:
            return random.choice([
                "alive unfortunately",
                "meh",
                "surviving",
                "been better been worse",
                "existing"
            ])
            
        elif any(thanks in message_lower for thanks in ['thank', 'thanks']):
            return random.choice([
                "yeah whatever",
                "k",
                "sure",
                "mhm",
                "don't mention it. seriously don't"
            ])
            
        else:
            # Generic fallback - should rarely be used since AI handles most cases
            return random.choice([
                "k",
                "sure",
                "cool story",
                "riveting",
                "fascinating",
                "mmhmm",
                "..."
            ])
    
    def clear_old_histories(self):
        """Clean up old conversation histories and memory data"""
        current_time = datetime.now()
        expired_users = []
        
        for user_id, history_data in self.conversation_history.items():
            if current_time - history_data['last_update'] > timedelta(seconds=self.history_ttl):
                expired_users.append(user_id)
        
        for user_id in expired_users:
            del self.conversation_history[user_id]
        
        if expired_users:
            logger.info(f"Cleared {len(expired_users)} expired conversation histories")
        
        # Also cleanup memory manager
        self.memory_manager.cleanup_old_memories()
    
    async def moderate_message(self, message: str) -> Dict[str, Any]:
        """
        Check if a message needs moderation (illegal content only)
        
        Returns:
            Dict with 'allowed' (bool) and 'reason' (str) if blocked
        """
        try:
            # Use OpenAI moderation API
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.moderations.create(input=message)
            )
            
            result = response.results[0]
            
            # We only care about severe violations (illegal content)
            severe_categories = [
                'hate/threatening',
                'self-harm/intent',
                'sexual/minors',
                'violence/graphic'
            ]
            
            for category in severe_categories:
                if category in result.categories and result.categories[category]:
                    return {
                        'allowed': False,
                        'reason': 'Message contains inappropriate content'
                    }
            
            return {'allowed': True, 'reason': None}
            
        except Exception as e:
            logger.error(f"Moderation check failed: {e}")
            # Allow message if moderation fails
            return {'allowed': True, 'reason': None}
    
    def _should_respond_in_group(self, message: str, bot_username: Optional[str], 
                                has_recent_activity: bool = False) -> bool:
        """
        Determine if bot should respond to a message in group chat
        
        Args:
            message: The message content
            bot_username: Bot's username (without @)
            has_recent_activity: Whether bot recently responded in this chat
            
        Returns:
            True if bot should respond, False otherwise
        """
        message_lower = message.lower()
        
        # Always respond to direct mentions
        if bot_username:
            # Check for @mentions
            if f"@{bot_username.lower()}" in message_lower:
                return True
            
            # Check for name mentions without @
            if "bigbalz" in message_lower:
                return True
        
        # Check for direct questions or greetings that seem directed at bot
        bot_indicators = [
            "hey bigbalz",
            "yo bigbalz", 
            "bigbalz,",
            "bigbalz?",
            "bigbalz!",
            "balz,",
            "balz?",
            "balz!",
            "@bigbalz",
            "big balz",  # Handle space variations
            "bigballz",  # Handle spelling variations
            "big ballz"
        ]
        
        if any(indicator in message_lower for indicator in bot_indicators):
            return True
        
        # Check if it's a reply to bot's previous message
        # (This would need to be implemented in telegram_handler)
        
        # Check for crypto contract addresses (always respond to these)
        # Simple check for Ethereum addresses
        if len(message.strip()) == 42 and message.strip().startswith('0x'):
            return True
        
        # Check for Solana addresses (base58, typically 32-44 chars)
        if 32 <= len(message.strip()) <= 44 and message.strip().isalnum():
            # More sophisticated check could be added
            return True
        
        # Check for questions specifically about crypto or bot functionality
        crypto_questions = [
            "analyze this",
            "check this",
            "what do you think",
            "is this a rug",
            "is this safe",
            "should i buy",
            "balz rank",
            "balz analysis"
        ]
        
        if any(question in message_lower for question in crypto_questions):
            return True
        
        # Generic questions at the start of a message (might be directed at bot)
        if message_lower.startswith(("what", "how", "can you", "could you", "will you", "do you")):
            # Only respond if it seems crypto-related or bot-related
            if any(term in message_lower for term in ["token", "crypto", "contract", "analyze", "balz", "you"]):
                return True
        
        # Check for messages that reference the bot in third person
        third_person_refs = [
            "ask bigbalz",
            "tell bigbalz",
            "bigbalz knows",
            "bigbalz can",
            "bigbalz will",
            "bigbalz should"
        ]
        
        if any(ref in message_lower for ref in third_person_refs):
            return True
        
        # Respond to thanks if it might be directed at bot
        if any(thanks in message_lower for thanks in ["thanks", "thank you", "thx", "ty"]):
            # Only if recent interaction or mentions bot
            if "balz" in message_lower or has_recent_activity or len(message_lower.split()) < 5:
                return True
        
        # If bot recently responded, be more lenient with follow-up questions
        if has_recent_activity:
            # Respond to follow-up questions or comments
            follow_up_indicators = [
                "what about", "how about", "and", "but", "also",
                "oh", "i see", "got it", "cool", "nice", "wow",
                "really", "seriously", "no way", "for real"
            ]
            if any(indicator in message_lower for indicator in follow_up_indicators):
                return True
            
            # Also respond to questions after recent activity
            if message.strip().endswith("?"):
                return True
        
        # Always respond to pineapple pizza mentions
        if "pineapple pizza" in message_lower or "pineapple on pizza" in message_lower:
            return True
        
        # Check for positive vibe opportunities - higher chance to respond
        positive_triggers = [
            "how's things", "how's everyone", "how are you", "what's up",
            "gm", "good morning", "hey everyone", "hello everyone",
            "vibes", "feeling", "mood"
        ]
        
        if any(trigger in message_lower for trigger in positive_triggers):
            # 70% chance to spread positive vibes
            import random
            if random.random() < 0.7:
                return True
        
        # Check for topics bot might have a funny take on (but be selective)
        funny_topics = [
            "crypto crash", "rug pull", "moon", "lambo",
            "scam", "ponzi", "pyramid scheme",
            "elon", "musk", "doge",
            "nft", "jpeg", "monkey picture",
            "to the moon", "when moon", "wen lambo",
            "bear market", "bull market", "pump", "gains"
        ]
        
        if any(topic in message_lower for topic in funny_topics):
            # Only jump in occasionally (not every time)
            import random
            # 30% chance to respond to interesting topics
            if random.random() < 0.3:
                return True
        
        # Don't respond to general chat
        return False
    
    def _has_recent_activity(self, chat_id: int) -> bool:
        """Check if bot has recently responded in this chat"""
        if chat_id not in self.group_activity:
            return False
        
        last_activity = self.group_activity[chat_id]
        time_diff = (datetime.now() - last_activity).seconds
        return time_diff < self.activity_window
    
    def _update_activity(self, chat_id: int):
        """Update the last activity time for a chat"""
        self.group_activity[chat_id] = datetime.now()
        
        # Clean up old activity entries
        current_time = datetime.now()
        expired_chats = [
            cid for cid, last_time in self.group_activity.items()
            if (current_time - last_time).seconds > self.activity_window * 10
        ]
        for cid in expired_chats:
            del self.group_activity[cid]
    
    def _check_ecosystem_questions(self, message: str) -> Optional[str]:
        """
        Check if message is asking about ecosystem projects and return beta response
        
        Args:
            message: The message to check
            
        Returns:
            Beta response if ecosystem question detected, None otherwise
        """
        message_lower = message.lower()
        
        # List of ecosystem terms to check (excluding BIGBALZ)
        ecosystem_terms = [
            "balz",  # Will check for standalone BALZ
            "$balz",  # Token symbol
            "pumpbalz",
            "pump balz",
            "balzdep",
            "balz dep",
            "faf",
            "balzback",
            "balz back",
            "josh gier",
            "musky balzac",
            "musky",
            "tokenomics",
            "roadmap",
            "whitepaper",
            "team",
            "developer",
            "founders",
            "ecosystem",
            "project"
        ]
        
        # Check if asking about ecosystem
        question_indicators = [
            "what is", "what's", "whats",
            "tell me about", "explain",
            "who is", "who's", "whos",
            "when", "roadmap", "tokenomics",
            "price", "buy", "where",
            "contract", "address"
        ]
        
        # First check if it's a question
        is_question = any(indicator in message_lower for indicator in question_indicators) or "?" in message
        
        if is_question:
            # Check for ecosystem terms
            for term in ecosystem_terms:
                if term == "balz":
                    # Special handling for "BALZ" to avoid matching "BIGBALZ"
                    # Check for standalone BALZ (not part of BIGBALZ)
                    # Word boundary patterns to match BALZ but not BIGBALZ
                    if re.search(r'\bbalz\b', message_lower):
                        # Make sure it's not part of BIGBALZ or BALZ ranking/classification
                        exclude_patterns = [
                            r'\bbig\s*balz',  # BIGBALZ
                            r'balz\s*(rank|ranking|classification|rating|analysis|score)',  # BALZ ranking system
                            r'(rank|ranking|classification|rating|analysis|score)\s*balz'  # ranking BALZ
                        ]
                        
                        if not any(re.search(pattern, message_lower) for pattern in exclude_patterns):
                            return self._get_beta_response()
                elif term in message_lower:
                    return self._get_beta_response()
        
        # Also check for direct mentions without question format
        direct_mentions = [
            "pumpbalz", "balzdep", "faf", "balzback",
            "josh gier", "musky balzac", "musky"
        ]
        
        for mention in direct_mentions:
            if mention in message_lower:
                # Check if they're asking for info (not just mentioning)
                info_context = [
                    "info", "information", "details", "about",
                    "?", "tell", "explain", "what", "who"
                ]
                if any(context in message_lower for context in info_context):
                    return self._get_beta_response()
        
        return None
    
    def _get_beta_response(self) -> str:
        """Return the beta response for ecosystem questions"""
        return (
            "I'm currently in BETA while the team tests my core capabilities. "
            "The full knowledge base for Musky Balzac and our ecosystem projects "
            "is being prepared for upload. Master Josh Gier and the team are "
            "building diligently, and I'll have complete project details available soon.\n\n"
            "For now, I'm focused on finding you moonshots and helping you try "
            "not to get rugged. Hit me up if you need me for something else!"
        )
    
    def _is_pineapple_pizza_mention(self, message: str) -> bool:
        """Check if message mentions pineapple pizza"""
        message_lower = message.lower()
        
        # Various ways people might mention pineapple pizza
        pineapple_patterns = [
            "pineapple pizza",
            "pineapple on pizza",
            "pizza with pineapple",
            "hawaiian pizza",  # The cursed pizza
            "pineapples on pizza",
            "🍍🍕",  # Emoji combo
            "🍍 🍕"
        ]
        
        # Check for any pattern
        return any(pattern in message_lower for pattern in pineapple_patterns)
    
    def _is_insult_or_troll(self, message: str) -> bool:
        """Check if message is insulting or trolling the bot"""
        message_lower = message.lower()
        
        # Direct insults
        insult_patterns = [
            "you suck",
            "you're stupid",
            "you're dumb",
            "you're trash",
            "you're garbage",
            "you're useless",
            "you're worthless",
            "you're terrible",
            "you're bad",
            "you're an idiot",
            "you idiot",
            "you moron",
            "you fool",
            "shut up",
            "stfu",
            "fuck you",
            "screw you",
            "you're retarded",
            "retard",
            "loser",
            "you're a loser",
            "you're pathetic",
            "bot sucks",
            "stupid bot",
            "dumb bot",
            "trash bot",
            "shitty bot",
            "worst bot",
            "hate this bot",
            "hate you"
        ]
        
        # Check if message is directed at bot and contains insult
        if "balz" in message_lower or "@" in message:
            return any(pattern in message_lower for pattern in insult_patterns)
        
        # Also check for standalone insults in short messages
        if len(message.split()) <= 3:
            return any(pattern in message_lower for pattern in insult_patterns)
        
        return False
    
    def _check_standard_questions(self, message: str) -> Optional[str]:
        """
        Check if message is asking for standard bot info
        
        Returns formatted response or None
        """
        message_lower = message.lower()
        
        # Check for intro/help requests
        intro_patterns = [
            "what can you do",
            "what do you do", 
            "how do you work",
            "help",
            "/help",
            "introduce yourself",
            "who are you",
            "tell me about yourself",
            "what are you",
            "what are your features",
            "what features",
            "show features",
            "list features"
        ]
        
        # Also check for variations with typos and spacing
        typo_patterns = [
            "waht can",  # common typo
            "what yo",   # spacing issues
            "wat can",
            "wut can",
            "tell us what",
            "tell me what",
            "what u can",
            "what you can"
        ]
        
        if any(pattern in message_lower for pattern in intro_patterns):
            return self._get_intro_message()
        
        # Check for typo variations asking about capabilities
        if any(pattern in message_lower for pattern in typo_patterns) and ("can" in message_lower or "do" in message_lower):
            return self._get_intro_message()
            
        # Also catch "yo u" variations specifically
        if "yo u" in message_lower and ("can" in message_lower or "do" in message_lower):
            return self._get_intro_message()
        
        # Check for BALZ Rank explanation
        balz_patterns = [
            "what is balz rank",
            "what's balz rank",
            "whats balz rank",
            "explain balz rank",
            "how does balz rank work",
            "balz classification",
            "what is balz classification",
            "balz ranking",
            "balz rating"
        ]
        
        if any(pattern in message_lower for pattern in balz_patterns):
            return self._get_balz_rank_explanation()
        
        # Check for moonshot explanation
        moonshot_patterns = [
            "how do you find moonshots",
            "how does moonshot work",
            "explain moonshots",
            "moonshot detection",
            "how do moonshots work",
            "what are moonshots"
        ]
        
        if any(pattern in message_lower for pattern in moonshot_patterns):
            return self._get_moonshot_explanation()
        
        # Check for rug detection explanation
        rug_patterns = [
            "how do you detect rugs",
            "how does rug detection work",
            "explain rug detection",
            "rug pull detection",
            "how do you find rugs",
            "rug detection"
        ]
        
        if any(pattern in message_lower for pattern in rug_patterns):
            return self._get_rug_detection_explanation()
        
        # Check for supported networks
        network_patterns = [
            "what networks",
            "which networks",
            "supported networks",
            "what chains",
            "which chains",
            "supported chains",
            "what blockchains"
        ]
        
        if any(pattern in message_lower for pattern in network_patterns):
            return self._get_supported_networks()
        
        return None
    
    def _get_intro_message(self) -> str:
        """Get the intro/help message"""
        return """Hey! BIGBALZ here. 

I'm Musky Balzac's AI agent, still in BETA but ready to help you navigate the crypto space.

Current Features

🔍 Token Analysis
Drop me any contract address and I'll break down the metrics, check if it's legit, and give you my honest take with BALZ Category rankings.

🚀 Moonshot Detection
I'm constantly scanning Solana, Base, and Ethereum for real opportunities. Ask "any fresh moonshots?" and I'll share what I've found.

⚠️ Rug Detection
I monitor for rug pulls in real-time and alert when I spot suspicious activity. Better safe than sorry.

💬 Just Chat
Feel free to talk normally - I'm not just a crypto bot, I'm here to have real conversations too.

🎨 AI Image Generation (SWITCHED OFF)
Create sick memes and charts with cutting-edge AI models. No more MS Paint garbage - we're talking premium visual content that'll make your bags look even better.

📱 Social Sentiment Charting (SWITCHED OFF)
I'll track what's buzzing across Twitter, Telegram, Discord, and Reddit. Real-time sentiment analysis so you know if the hype is real or just another pump-and-dump circle jerk.

Supported Networks: Solana, Base, Ethereum  

Fair warning: I call it like I see it. If your token is trash, I'll tell you it's trash. If it's solid, you'll know that too.


Functions Coming Soon

🔍 Full Token Health Check & BALZ Rank
Deep dive analysis with my proprietary BALZ scoring system. I'll rate your shitcoin from MEGA BALZ (moon mission) to NO BALZ (rug incoming).

👀 Shill Detection & Rewards
I can see if you're actually tweeting about projects or just lurking like a coward. Shill for good projects? Get rewarded. Stay silent on gems? Get rekt by FOMO.

 🚀 Private BalzBack Applications
Project leaders can slide into my DMs with their BalzBack submissions. Exclusive access, no public shilling required.
Potential Features

Advanced Trading Tools

💰 Multi-Network Arbitrage Finder - Spot price differences across chains faster than MEV bots

🐋 Whale Trade Tracker - Monitor big money moves with transaction analysis

⚡️ Flash Pump Detector - Real-time alerts for unusual volume/price action

🎯 Token Correlation Matrix - See which coins move together (spoiler: they all dump together)

Get Started

Drop a contract address or just ask what's on your mind!"""
    
    def _get_balz_rank_explanation(self) -> str:
        """Get BALZ Rank explanation"""
        return """🎯 BALZ Rank - My Token Classification System

I analyze 5 key metrics to tell you if a token is worth it or trash.


📊 VOLUME TIERS (24h Trading)

• Dead: $0 - $1K (ghost town)
• Struggling: $1K - $10K
• Active: $10K - $100K
• Hot: $100K - $1M (real action)
• Explosive: $1M+ (holy shit)


💧 LIQUIDITY TIERS (Can you exit?)

• Risky: $0 - $25K (you're trapped)
• Thin: $25K - $100K
• Decent: $100K - $300K
• Deep: $300K - $1M (easy in/out)
• Prime: $1M+ (whale territory)


💰 MARKET CAP & FDV

Shows if you're early or exit liquidity


⚠️ FDV/MC RATIO (Hidden dumps)

• Clean: 1-1.5x (fair launch)
• Caution: 1.5-3x
• Heavy: 3-7x
• Bloated: 7-10x
• Red Flag: 10x+ (90% hidden tokens!)


🎲 FINAL RANKINGS:

⛔ TRASH = Bad liquidity = RUN
🔶 RISKY = Gambling only
⚠️ CAUTION = Research more
🚀 OPPORTUNITY = LFG

Each rank tells you exactly what you're getting into."""
    
    def _get_moonshot_explanation(self) -> str:
        """Get moonshot detection explanation"""
        return """🚀 Moonshot Detection - Live 24/7 Scanning

I hunt for REAL pumps across all networks every 60 seconds.


🌟 100x MOONSHOT (5-min explosions)

• +50% in 5 minutes
• $5K+ liquidity
• $10K+ daily volume
• 50+ transactions

Catches microcaps taking off NOW


⚡ 10x MOONSHOT (hourly movers)

• +25% in 1 hour
• $15K+ liquidity
• $25K+ daily volume
• 75+ transactions

Strong momentum plays


💰 2x MOONSHOT (daily gainers)

• +15% in 24 hours
• $50K+ liquidity
• $50K+ daily volume
• 100+ transactions

Steady organic growth


Why these numbers?
✓ Liquidity = You can actually exit
✓ Volume = Real interest, not one whale
✓ Transactions = Community buying

Type: "any moonshots?" or wait for alerts
1-hour cooldown per token to avoid spam"""
    
    def _get_rug_detection_explanation(self) -> str:
        """Get rug detection explanation"""
        return """🚨 Rug Detection - 60-Second Monitoring

I watch for the classic exit scam patterns.


💀 RUG INDICATORS:


1. Liquidity Drain

• 80%+ sudden drop
• From $50K → $5K = RUG
• Devs pulling the pool


2. Price Nuke

• 90%+ price crash
• Not a "dip" - it's over
• Massive token dumps


3. Death Spiral

• Low liquidity + crashing price
• Under $1K liquidity = ☠️
• No escape route


⏱️ Why 60-second checks?

Rugs happen FAST. By the time you refresh, it's gone.


📍 What I track:

- Current vs 1hr ago
- Current vs 24hr ago
- Current vs 1 week ago


When I spot a rug, I alert IMMEDIATELY.
No buttons. No analysis. Just warnings.

Prevention tip: Check BALZ Rank first!"""
    
    def _get_supported_networks(self) -> str:
        """Get supported networks list"""
        return """🌐 Supported Networks

Currently supporting:

• Ethereum (ETH)
• Solana (SOL)  
• Base (BASE)
• BNB Smart Chain (BSC)

Just drop any contract from these networks and I'll auto-detect it.

Example formats:
• ETH/BSC/Base: 0x123...abc
• Solana: 7EYnhQoR9YM3...pump"""
    
    def _get_personality_context(self, personality_level) -> str:
        """Get personality context based on interaction history"""
        from .response_memory import PersonalityLevel
        
        if personality_level == PersonalityLevel.FRESH:
            return "This is a new user you haven't talked to much. Be your usual self but maybe slightly more welcoming."
        elif personality_level == PersonalityLevel.FAMILIAR:
            return "You've chatted with this user a few times. You can be more casual and reference that you've talked before."
        else:  # ESTABLISHED
            return "This is a regular you know well. Be more familiar, maybe reference past conversations, and show that you remember them."
    
    def _get_pineapple_fallback_responses(self, personality_level) -> List[str]:
        """Get fallback responses for pineapple pizza when phrase is in cooldown"""
        from .response_memory import PersonalityLevel
        
        base_responses = [
            "we've been through this already",
            "you know how i feel about that",
            "not this again",
            "seriously?",
            "moving on..."
        ]
        
        if personality_level == PersonalityLevel.ESTABLISHED:
            base_responses.extend([
                "i thought we settled this",
                "you're really gonna make me say it again?",
                "we've had this conversation"
            ])
        
        return base_responses
    
    def _get_troll_response_context(self, personality_level) -> str:
        """Get troll response context based on personality level"""
        from .response_memory import PersonalityLevel
        
        base_context = "Someone is trying to insult or troll you. Give them a short, intelligent, savage comeback. Be creative and savage but not defensive. Keep it brief and cutting."
        
        if personality_level == PersonalityLevel.ESTABLISHED:
            return base_context + " Since you know this user, you can be extra savage and personal in your roast."
        else:
            return base_context
    
    def _get_troll_fallback_responses(self, personality_level) -> List[str]:
        """Get fallback responses for troll attempts when phrase is in cooldown"""
        from .response_memory import PersonalityLevel
        
        base_responses = [
            "k",
            "sure buddy",
            "riveting",
            "cool story",
            "anyway...",
            "mmhmm"
        ]
        
        if personality_level == PersonalityLevel.ESTABLISHED:
            base_responses.extend([
                "you're really trying this again?",
                "we doing this dance again?",
                "thought you'd learned by now"
            ])
        
        return base_responses
    
