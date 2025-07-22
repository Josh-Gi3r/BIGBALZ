"""
BIGBALZ Bot - Core Telegram Handler
Manages all Telegram interactions and message routing
"""

import logging
import asyncio
import time
from typing import Optional, Dict, List, Tuple
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

logger = logging.getLogger(__name__)


class TelegramBotHandler:
    """Main Telegram bot handler for BIGBALZ"""
    
    def __init__(self, token: str, api_client=None, balz_engine=None, 
                 button_handler=None, session_manager=None, conversation_handler=None,
                 background_monitor=None, settings=None):
        """
        Initialize the Telegram bot handler
        
        Args:
            token: Telegram bot token
            api_client: GeckoTerminal API client
            balz_engine: BALZ classification engine
            button_handler: Button interaction handler
            session_manager: Session state manager
            conversation_handler: AI conversation handler for general chat
            background_monitor: Background monitoring system
            settings: Application settings configuration
        """
        self.token = token
        self.api_client = api_client
        self.balz_engine = balz_engine
        self.button_handler = button_handler
        self.session_manager = session_manager
        self.conversation_handler = conversation_handler
        self.background_monitor = background_monitor
        self.settings = settings
        self.application = None
        
        # Track chats for alerts
        self.alert_chats = set()
        # Pre-register your chat so it persists across restarts
        self.alert_chats.add(-1002846188663)  # Your group chat
        
        # Track messages for auto-deletion after 25 minutes
        self.scheduled_deletions: Dict[str, Tuple[int, float]] = {}  # message_key -> (chat_id, deletion_time)
        self.deletion_lock = asyncio.Lock()
        self.cleanup_task = None
        
    def setup(self):
        """Set up the bot application and handlers"""
        # Create application
        self.application = Application.builder().token(self.token).build()
        
        # Add command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("about", self.about_command))
        
        # Add message handler for contract addresses
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
        
        # Add callback query handler for buttons
        if self.button_handler:
            self.application.add_handler(
                CallbackQueryHandler(self.button_handler.handle_button_callback)
            )
        
        # Add new member handler
        self.application.add_handler(
            MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, self.handle_new_members)
        )
        
        logger.info("Telegram bot handlers configured successfully")
        logger.info(f"Pre-registered {len(self.alert_chats)} chat(s) for alerts")
    
    def register_chat_for_alerts(self, chat_id: int):
        """Register a chat to receive alerts"""
        if chat_id not in self.alert_chats:
            self.alert_chats.add(chat_id)
            logger.info(f"Registered chat {chat_id} for alerts. Total chats: {len(self.alert_chats)}")
    
    async def broadcast_alert(self, message: str, reply_markup=None, alert_context=None):
        """Broadcast alert to all registered chats with auto-deletion"""
        logger.info(f"📢 broadcast_alert called with message: {message[:100]}...")
        logger.info(f"📢 Alert chats registered: {len(self.alert_chats) if self.alert_chats else 0}")
        
        if not self.alert_chats:
            logger.warning("❌ No chats registered for alerts")
            return
        
        success_count = 0
        deletion_time = time.time() + (25 * 60)  # 25 minutes from now
        
        for chat_id in self.alert_chats.copy():  # Copy to avoid modification during iteration
            try:
                logger.info(f"📤 Sending alert to chat {chat_id}")
                sent_message = await self.application.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                success_count += 1
                logger.info(f"✅ Alert sent successfully to chat {chat_id}")
                
                # Store alert context for button handlers if provided
                if alert_context:
                    session = self.session_manager.get_session(chat_id, 0)  # Use 0 for broadcast user_id
                    if not session:
                        session = self.session_manager.create_session(
                            chat_id=chat_id,
                            user_id=0,
                            token_name=alert_context.get('symbol', 'Alert'),
                            contract=alert_context.get('contract', ''),
                            network=alert_context.get('network', ''),
                            token_data={}
                        )
                    session.alert_context = alert_context
                    logger.info(f"📝 Stored alert context for chat {chat_id}: {alert_context}")
                
                # Schedule deletion for all broadcast messages (buttons or not)
                await self._schedule_message_deletion(chat_id, sent_message.message_id, deletion_time)
                    
            except Exception as e:
                logger.error(f"Failed to send alert to chat {chat_id}: {e}")
                # Remove chat if it's no longer accessible
                if "chat not found" in str(e).lower():
                    self.alert_chats.discard(chat_id)
        
        logger.info(f"Alert sent to {success_count}/{len(self.alert_chats)} chats")
    
    async def _schedule_message_deletion(self, chat_id: int, message_id: int, deletion_time: float):
        """Schedule a message for deletion"""
        async with self.deletion_lock:
            key = f"{chat_id}_{message_id}"
            self.scheduled_deletions[key] = (chat_id, deletion_time)
            logger.info(f"📅 Scheduled deletion for message {message_id} in chat {chat_id} at {deletion_time} (in {(deletion_time - time.time())/60:.1f} minutes)")
    
    async def _cleanup_expired_messages(self):
        """Background task to delete expired messages"""
        logger.info("🧹 Message cleanup task started")
        
        while True:
            try:
                current_time = time.time()
                messages_to_delete = []
                
                async with self.deletion_lock:
                    # Find expired messages
                    total_scheduled = len(self.scheduled_deletions)
                    logger.debug(f"🔍 Checking {total_scheduled} scheduled deletions at {current_time}")
                    
                    for key, (chat_id, deletion_time) in self.scheduled_deletions.items():
                        if current_time >= deletion_time:
                            messages_to_delete.append((key, chat_id))
                            logger.debug(f"⏰ Message {key} expired (scheduled: {deletion_time}, current: {current_time})")
                
                # Delete expired messages
                for key, chat_id in messages_to_delete:
                    try:
                        message_id = int(key.split('_')[1])
                        
                        if not self.application or not self.application.bot:
                            logger.error(f"❌ Bot application not initialized - cannot delete message {message_id}")
                            continue
                            
                        await self.application.bot.delete_message(chat_id=chat_id, message_id=message_id)
                        
                        async with self.deletion_lock:
                            del self.scheduled_deletions[key]
                            
                        logger.info(f"🗑️ Successfully deleted expired message {message_id} from chat {chat_id}")
                    except Exception as e:
                        logger.error(f"❌ Failed to delete message {key}: {e}")
                        # Remove from tracking even if deletion failed
                        async with self.deletion_lock:
                            self.scheduled_deletions.pop(key, None)
                
                if messages_to_delete:
                    logger.info(f"🧹 Cleaned up {len(messages_to_delete)} expired messages")
                elif len(self.scheduled_deletions) > 0:
                    logger.debug(f"⏳ {len(self.scheduled_deletions)} messages still scheduled for future deletion")
                
                # Check every 30 seconds
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"💥 Error in cleanup task: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait longer on error
    
    async def start_cleanup_task(self):
        """Start the message cleanup background task"""
        if not self.cleanup_task:
            if not self.application:
                logger.warning("⚠️ Bot application not initialized yet - cleanup task may fail")
            self.cleanup_task = asyncio.create_task(self._cleanup_expired_messages())
            logger.info("🧹 Message cleanup task created and started")
    
    async def stop_cleanup_task(self):
        """Stop the cleanup task"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            self.cleanup_task = None
            logger.info("Message cleanup task stopped")
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        # Check if this is a private chat
        if update.effective_chat.type == 'private':
            user_id = update.effective_user.id
            
            if user_id not in self.settings.allowed_dm_users:
                await update.message.reply_text(
                    "commands in my DMs? really?\n\ngo to @MUSKYBALZAC if you need help. i don't do private tutorials"
                )
                return
        
        welcome_message = """Welcome! I'm BIGBALZ.

I'm here to chat, share insights, and keep our community engaging and fun. Feel free to talk about anything - crypto, memes, or just life in general.

If you'd like me to analyze a crypto token, just send me the contract address and I'll give you my comprehensive BALZ analysis:
• **TRASH** - Avoid at all costs
• **RISKY** - High-risk gamble
• **CAUTION** - Proceed carefully
• **OPPORTUNITY** - Strong potential

Looking forward to chatting with you!"""
        
        await update.message.reply_text(
            welcome_message,
            parse_mode='Markdown'
        )
        
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        # Check if this is a private chat
        if update.effective_chat.type == 'private':
            user_id = update.effective_user.id
            
            if user_id not in self.settings.allowed_dm_users:
                await update.message.reply_text(
                    "need help? in private? sus...\n\njoin @MUSKYBALZAC and ask there. i'm sure someone will help (maybe)"
                )
                return
        
        help_message = """📚 **BIGBALZ Bot Help**

**Commands:**
• /start - Welcome message
• /help - This help message
• /about - About BIGBALZ Bot

**How to analyze a token:**
1. Copy the token's contract address
2. Send it to me in a message
3. I'll analyze and show you:
   - Token overview with key metrics
   - Interactive buttons for more info
   - BALZ classification and analysis

**Button Functions:**
• 📱 **Socials** - Project links and description
• ⚖️ **BALZ Rank** - Detailed classification analysis
• 🐋 **Whale Tracker** - Large holder analysis
• 🔄 **Refresh Price** - Get updated data

**Background Monitoring:**
I also monitor for:
• 🚀 Moonshots (rapid price increases)
• 🚨 Rug pulls (liquidity drains)

**Need support?**
Contact: @YourSupportHandle"""
        
        await update.message.reply_text(
            help_message,
            parse_mode='Markdown'
        )
        
    async def about_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /about command"""
        # Check if this is a private chat
        if update.effective_chat.type == 'private':
            user_id = update.effective_user.id
            
            if user_id not in self.settings.allowed_dm_users:
                await update.message.reply_text(
                    "wanna know about me? in private? creepy...\n\n@MUSKYBALZAC is where i share my life story"
                )
                return
        
        about_message = """**About BIGBALZ**

I'm a community bot designed to engage, entertain, and occasionally enlighten. I enjoy good conversation, whether it's about crypto, memes, or anything else that interests you.

**What I can do:**
• Chat naturally about various topics
• Welcome new community members
• Analyze crypto tokens with my BALZ classification system
• Keep conversations engaging and friendly

**Token Analysis:**
When you share a contract address, I provide comprehensive analysis with my BALZ ranking:
• **TRASH** - Serious concerns identified
• **RISKY** - High-risk investment
• **CAUTION** - Mixed signals, research needed
• **OPPORTUNITY** - Strong potential identified

**Community Focus:**
I'm here to make our community a great place to hang out, learn, and share ideas.

**Version:** 2.0.0"""
        
        await update.message.reply_text(
            about_message,
            parse_mode='Markdown'
        )
        
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming text messages (contract addresses and general chat)"""
        if not update.message or not update.message.text:
            return
            
        message_text = update.message.text.strip()
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        username = update.effective_user.first_name or update.effective_user.username
        
        # Check if this is a private chat
        if update.effective_chat.type == 'private':
            # Only allow specific user ID (Josh)
            
            if user_id not in self.settings.allowed_dm_users:
                # Send cheeky response about sliding into DMs
                dm_responses = [
                    "whoa whoa whoa... sliding into my DMs? i don't do private shows\n\nhead to @MUSKYBALZAC and let's talk there. i'm not that kind of bot",
                    "yo this ain't tinder. i don't do DMs\n\ntake it to the main chat @MUSKYBALZAC where everyone can see your shame",
                    "excuse me? trying to get me alone? suspicious...\n\ngo to @MUSKYBALZAC if you wanna talk. i like witnesses",
                    "nah fam, i don't know you like that\n\n@MUSKYBALZAC is where the party's at. see you there",
                    "sliding into my DMs? what is this, 2018?\n\npublic chat only bro → @MUSKYBALZAC",
                    "i don't do private consultations. my therapist said i need boundaries\n\njoin @MUSKYBALZAC and we can talk there"
                ]
                import random
                await update.message.reply_text(random.choice(dm_responses))
                return
        
        # Log the incoming message
        logger.info(f"Received message from user {user_id}: {message_text}")
        
        # Register chat for alerts (moonshots, rugs, status reports)
        self.register_chat_for_alerts(chat_id)
        
        # Check for gem research and moonshot/rug queries first (before other processing)
        message_lower = message_text.lower()
        
        # Check for gem research triggers (new pattern from spec)
        if self._is_gem_research_query(message_lower):
            # Get the choice message (moonshots vs gem research)
            if not hasattr(self, 'gem_research_handler') or not self.gem_research_handler:
                await update.message.reply_text("Gem research feature is initializing. Try again in a moment.")
                return
            
            choice_message, choice_buttons = self.gem_research_handler.get_choice_message()
            sent_msg = await update.message.reply_text(
                choice_message,
                parse_mode='Markdown',
                reply_markup=choice_buttons
            )
            # Schedule deletion
            deletion_time = time.time() + (25 * 60)
            await self._schedule_message_deletion(chat_id, sent_msg.message_id, deletion_time)
            return
        
        if self._is_moonshot_query(message_lower):
            response = self._get_moonshot_summary()
            if response == "MOONSHOT_ALERT_WITH_BUTTONS":
                # Send moonshot with buttons
                alert_data = self._pending_moonshot_alert
                sent_msg = await update.message.reply_text(
                    alert_data['message'],
                    parse_mode='Markdown',
                    reply_markup=alert_data['buttons']
                )
                # Schedule deletion
                deletion_time = time.time() + (25 * 60)
                await self._schedule_message_deletion(chat_id, sent_msg.message_id, deletion_time)
                self._pending_moonshot_alert = None
            else:
                await update.message.reply_text(response)
            return
        
        if self._is_rug_query(message_lower):
            response = self._get_rug_summary()
            if response == "RUG_ALERT_WITH_BUTTONS":
                # Send rug with buttons
                alert_data = self._pending_rug_alert
                sent_msg = await update.message.reply_text(
                    alert_data['message'],
                    parse_mode='Markdown',
                    reply_markup=alert_data['buttons']
                )
                # Schedule deletion
                deletion_time = time.time() + (25 * 60)
                await self._schedule_message_deletion(chat_id, sent_msg.message_id, deletion_time)
                self._pending_rug_alert = None
            else:
                await update.message.reply_text(response)
            return
        
        # Check if dependencies are available
        if not all([self.api_client, self.balz_engine, self.button_handler, 
                    self.session_manager]):
            await update.message.reply_text(
                "I'm still warming up. Give me a moment and try again.",
                parse_mode='Markdown'
            )
            return
        
        # Import validator
        from src.utils.validators import ContractValidator
        
        # First check if it's a valid contract address
        is_valid, network, error = ContractValidator.validate_contract(message_text)
        
        # If it's not a contract address, handle as general chat
        if not is_valid:
            # Use AI conversation handler if available
            if self.conversation_handler:
                try:
                    # Show typing indicator while AI processes
                    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
                    
                    # Check moderation first
                    moderation_result = await self.conversation_handler.moderate_message(message_text)
                    if not moderation_result['allowed']:
                        await update.message.reply_text(
                            "Let's keep things friendly here.",
                            parse_mode='Markdown'
                        )
                        return
                    
                    # Determine if this is a group chat
                    is_group_chat = update.effective_chat.type in ['group', 'supergroup']
                    
                    # Check if message is a reply to the bot
                    is_reply_to_bot = False
                    if update.message.reply_to_message and update.message.reply_to_message.from_user:
                        is_reply_to_bot = update.message.reply_to_message.from_user.id == context.bot.id
                    
                    # Get bot username for mention detection
                    bot_username = context.bot.username
                    
                    # Generate AI response (might return None in group chats)
                    response = await self.conversation_handler.get_response(
                        message_text, 
                        user_id,
                        username,
                        is_group_chat=is_group_chat,
                        bot_username=bot_username,
                        is_reply_to_bot=is_reply_to_bot,
                        chat_id=chat_id
                    )
                    
                    # Only reply if bot should respond
                    if response:
                        await update.message.reply_text(response, parse_mode='Markdown')
                    return
                except Exception as e:
                    logger.error(f"Error in conversation handler: {e}")
                    # Fall through to basic responses
            
            # Fallback to basic pattern matching if no AI handler
            # Check if it's a greeting or general message
            greetings = ['hi', 'hello', 'hey', 'sup', 'yo', 'gm', 'good morning', 'wassup', 'what\'s up']
            if any(greeting in message_text.lower() for greeting in greetings):
                await update.message.reply_text(
                    "Hello there! Great to see you.\n\n"
                    "I'm BIGBALZ, here to chat about anything you'd like - crypto, memes, or just life in general.\n\n"
                    "If you have a token contract you'd like me to analyze, just send it my way and I'll give you the full breakdown.",
                    parse_mode='Markdown'
                )
                return
            
            # Check for questions about how to use
            help_keywords = ['how', 'what', 'help', 'use', 'analyze', 'check']
            if any(keyword in message_text.lower() for keyword in help_keywords):
                # Show typing for consistency
                await context.bot.send_chat_action(chat_id=chat_id, action="typing")
                await update.message.reply_text(
                    "📚 **How to use BIGBALZ Bot:**\n\n"
                    "1️⃣ Copy a token's contract address\n"
                    "2️⃣ Send it to me\n"
                    "3️⃣ I'll analyze it and show you:\n"
                    "   • Token metrics (price, MC, volume)\n"
                    "   • BALZ classification\n"
                    "   • Interactive buttons for more info\n\n"
                    "**Example addresses:**\n"
                    "ETH: `0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE`\n"
                    "SOL: `EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`\n\n"
                    "Try sending one! 🚀",
                    parse_mode='Markdown'
                )
                return
            
            # Check if user is asking about a token in context
            session = self.session_manager.get_session(chat_id, user_id)
            if session and session.current_token:
                # User might be asking about the last analyzed token
                token_keywords = ['price', 'moon', 'dump', 'rug', 'scam', 'buy', 'sell', 'hold']
                if any(keyword in message_text.lower() for keyword in token_keywords):
                    await update.message.reply_text(
                        f"💭 Asking about **{session.current_token}**?\n\n"
                        f"Use the buttons below my last analysis, or send a new contract address!\n\n"
                        f"Want fresh data? Try the **🔄 Refresh Price** button.",
                        parse_mode='Markdown'
                    )
                    return
            
            # Check for common crypto questions
            crypto_terms = ['shitcoin', 'memecoin', 'degen', 'ape', 'fomo', 'diamond hands', 'paper hands']
            if any(term in message_text.lower() for term in crypto_terms):
                await update.message.reply_text(
                    "😏 I see you speak crypto!\n\n"
                    "Send me a contract and I'll tell you if it's worth aping or if you should run.\n\n"
                    "Remember: I classify tokens as:\n"
                    "⛔ TRASH - Stay away!\n"
                    "🔶 RISKY - Degen play only\n"
                    "⚠️ CAUTION - Do your research\n"
                    "🚀 OPPORTUNITY - Potential gem\n\n"
                    "Drop a contract, let's see what we got! 💎🙌",
                    parse_mode='Markdown'
                )
                return
            
            # For other messages, suggest sending a contract
            await update.message.reply_text(
                "🤖 I'm a token analysis bot!\n\n"
                "Send me a contract address to analyze, or try:\n"
                "• /help - For detailed instructions\n"
                "• /about - Learn more about BALZ\n\n"
                "Got a token to check? Send the contract! 📊",
                parse_mode='Markdown'
            )
            return
        
        # If we get here, it's a valid contract address
        # Show typing indicator
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        
        # Send processing message
        processing_msg = await update.message.reply_text(
            "🔍 Analyzing contract...",
            parse_mode='Markdown'
        )
        
        try:
            
            # Fetch token data from API - try multiple networks
            token_data = await self.api_client.get_token_info_multi_network(message_text)
            
            if not token_data:
                await processing_msg.edit_text(
                    "❌ **Token Not Found**\n\n"
                    "Couldn't find this token on any supported network (ETH, Base, BSC, Solana).\n\n"
                    "Please check:\n"
                    "• Contract address is correct\n"
                    "• Token is listed on GeckoTerminal\n"
                    "• Token has sufficient liquidity",
                    parse_mode='Markdown'
                )
                return
            
            # Create session
            session = self.session_manager.create_session(
                chat_id=chat_id,
                user_id=user_id,
                token_name=f"{token_data.name} ({token_data.symbol})",
                contract=message_text,
                network=token_data.network,  # Use network from token data
                token_data=token_data.__dict__
            )
            
            # Format token overview message
            from src.bot.message_formatter import MessageFormatter
            overview_message = MessageFormatter.format_token_overview(token_data)
            
            # Create buttons
            buttons = self.button_handler.create_token_overview_buttons()
            
            # Edit message with token overview and buttons
            await processing_msg.edit_text(
                overview_message,
                parse_mode='Markdown',
                reply_markup=buttons
            )
            
            # Schedule deletion for messages with buttons
            deletion_time = time.time() + (25 * 60)  # 25 minutes
            await self._schedule_message_deletion(chat_id, processing_msg.message_id, deletion_time)
            
            logger.info(f"Successfully analyzed token {token_data.symbol} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            await processing_msg.edit_text(
                "❌ **Error Processing Request**\n\n"
                "An error occurred while analyzing the token. Please try again later.",
                parse_mode='Markdown'
            )
    
    async def handle_new_members(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle new members joining the chat"""
        if not update.message.new_chat_members:
            return
            
        chat_id = update.effective_chat.id
        
        for new_member in update.message.new_chat_members:
            # Skip if it's the bot itself
            if new_member.id == context.bot.id:
                continue
                
            # Show typing while generating welcome
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
                
            username = new_member.first_name or new_member.username or "friend"
            
            # Use AI handler for personalized welcome if available
            if self.conversation_handler:
                try:
                    # Group chats always have new members join in groups
                    is_group_chat = update.effective_chat.type in ['group', 'supergroup']
                    
                    welcome_message = await self.conversation_handler.get_response(
                        f"Welcome new member {username} to our community",
                        new_member.id,
                        username,
                        is_new_member=True,
                        is_group_chat=is_group_chat,
                        bot_username=context.bot.username
                    )
                    if welcome_message:
                        await update.message.reply_text(welcome_message, parse_mode='Markdown')
                except Exception as e:
                    logger.error(f"Error generating welcome message: {e}")
                    # Fall through to default welcome
            
            # Fallback welcome message
            else:
                await update.message.reply_text(
                    f"Welcome to the community, {username}! "
                    f"Great to have you here. Feel free to ask me anything or just chat. "
                    f"If you need help with crypto analysis, just send me a contract address.",
                    parse_mode='Markdown'
                )
    
    async def broadcast_message(self, message: str, reply_markup=None):
        """
        Broadcast a message to all active chats
        Used for moonshot/rug alerts
        
        Args:
            message: Message text to broadcast
            reply_markup: Optional inline keyboard markup
        """
        # This would need to be implemented with a proper chat storage system
        # For now, it's a placeholder for the monitoring system
        logger.info(f"Broadcasting message: {message[:50]}...")
    
    def _is_gem_research_query(self, message_lower: str) -> bool:
        """Check if message contains gem research trigger words"""
        # Existing triggers (moonshot/gem queries) - these will show choice
        existing_triggers = [
            "moonshot", "moonshots", "gem", "gems", "moon", "gains", "pumping", "mooning"
        ]
        
        # New triggers (research-specific) - these will show choice
        research_triggers = [
            "research", "find", "look for", "search", "scan for", "help me find", "explore", "discover"
        ]
        
        # Combined triggers
        combined_triggers = [
            "research gems", "find gems", "look for moonshots", "search tokens"
        ]
        
        # Check for any trigger
        all_triggers = existing_triggers + research_triggers + combined_triggers
        return any(trigger in message_lower for trigger in all_triggers)
    
    def _is_moonshot_query(self, message_lower: str) -> bool:
        """Check if message is asking about moonshots or gems (legacy specific queries)"""
        moonshot_patterns = [
            "any moonshots",
            "any moonshot", 
            "recent moonshots",
            "show moonshots",
            "what moonshots",
            "found any moonshots",
            "any gems",
            "any gem",
            "recent gems", 
            "show gems",
            "what gems",
            "found any gems"
        ]
        return any(pattern in message_lower for pattern in moonshot_patterns)
    
    def _is_rug_query(self, message_lower: str) -> bool:
        """Check if message is asking about rugs"""
        rug_patterns = [
            "any rugs",
            "any rug",
            "recent rugs", 
            "show rugs",
            "what rugs",
            "found any rugs"
        ]
        return any(pattern in message_lower for pattern in rug_patterns)
    
    def _get_moonshot_summary(self) -> str:
        """Get summary of recent moonshots from background monitor"""
        try:
            if self.background_monitor:
                monitor = self.background_monitor
                
                # Count moonshots from last 24 hours
                import time
                cutoff_time = time.time() - (24 * 60 * 60)
                
                moonshots = []
                for contract, moonshot_alert in monitor.detected_moonshots.items():
                    if moonshot_alert.timestamp.timestamp() >= cutoff_time:
                        moonshots.append(moonshot_alert)
                
                if not moonshots:
                    return "no moonshots in the last 24 hours. market's dead rn"
                
                # Sort by timestamp (newest first)
                moonshots.sort(key=lambda x: x.timestamp, reverse=True)
                
                # If only one moonshot, show it with buttons
                if len(moonshots) == 1:
                    moonshot = moonshots[0]
                    # Format the moonshot message
                    message = monitor._format_moonshot_message(moonshot)
                    
                    # Create buttons for this moonshot
                    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                    buttons = InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("📊 Token Details", callback_data=f"alert_analyze_{moonshot.network}_{moonshot.contract}"),
                            InlineKeyboardButton("📱 Socials", callback_data=f"alert_socials_{moonshot.network}_{moonshot.contract}")
                        ],
                        [
                            InlineKeyboardButton("🐋 Whale Tracker", callback_data=f"alert_whale_{moonshot.network}_{moonshot.contract}"),
                            InlineKeyboardButton("⚖️ BALZ Rank", callback_data=f"alert_balz_{moonshot.network}_{moonshot.contract}")
                        ]
                    ])
                    
                    # Store for async sending
                    self._pending_moonshot_alert = {
                        'message': message,
                        'buttons': buttons
                    }
                    return "MOONSHOT_ALERT_WITH_BUTTONS"
                
                # Multiple moonshots - show first with navigation
                else:
                    # Store moonshots in session for navigation
                    self._moonshot_list = moonshots
                    self._moonshot_index = 0
                    
                    moonshot = moonshots[0]
                    message = monitor._format_moonshot_message(moonshot)
                    
                    # Create buttons with Next option
                    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                    buttons = InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("📊 Token Details", callback_data=f"alert_analyze_{moonshot.network}_{moonshot.contract}"),
                            InlineKeyboardButton("📱 Socials", callback_data=f"alert_socials_{moonshot.network}_{moonshot.contract}")
                        ],
                        [
                            InlineKeyboardButton("🐋 Whale Tracker", callback_data=f"alert_whale_{moonshot.network}_{moonshot.contract}"),
                            InlineKeyboardButton("⚖️ BALZ Rank", callback_data=f"alert_balz_{moonshot.network}_{moonshot.contract}")
                        ],
                        [
                            InlineKeyboardButton(f"Next → ({len(moonshots)-1} more)", callback_data="next_moonshot")
                        ]
                    ])
                    
                    # Store for async sending
                    self._pending_moonshot_alert = {
                        'message': message,
                        'buttons': buttons
                    }
                    return "MOONSHOT_ALERT_WITH_BUTTONS"
            else:
                return "moonshot tracker not running yet. gimme a minute"
        except Exception as e:
            logger.error(f"Error getting moonshot summary: {e}")
            return "moonshot tracker broke. probably nothing"
    
    def _get_rug_summary(self) -> str:
        """Get summary of recent rugs from background monitor"""
        try:
            if self.background_monitor:
                monitor = self.background_monitor
                
                # Count rugs from last 24 hours
                import time
                cutoff_time = time.time() - (24 * 60 * 60)
                
                rugs = []
                for contract, rug_alert in monitor.detected_rugs.items():
                    if rug_alert.timestamp.timestamp() >= cutoff_time:
                        rugs.append(rug_alert)
                
                if not rugs:
                    return "no rugs in the last 24 hours. surprisingly peaceful"
                
                # Sort by timestamp (newest first)
                rugs.sort(key=lambda x: x.timestamp, reverse=True)
                
                # If only one rug, show it with buttons
                if len(rugs) == 1:
                    rug = rugs[0]
                    # Format the rug message
                    message = monitor._format_rug_message(rug)
                    
                    # Create buttons for this rug
                    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                    buttons = InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("📊 Token Details", callback_data=f"alert_analyze_{rug.network}_{rug.contract}"),
                            InlineKeyboardButton("📱 Socials", callback_data=f"alert_socials_{rug.network}_{rug.contract}")
                        ],
                        [
                            InlineKeyboardButton("🐋 Whale Tracker", callback_data=f"alert_whale_{rug.network}_{rug.contract}"),
                            InlineKeyboardButton("⚖️ BALZ Rank", callback_data=f"alert_balz_{rug.network}_{rug.contract}")
                        ]
                    ])
                    
                    # Store for async sending
                    self._pending_rug_alert = {
                        'message': message,
                        'buttons': buttons
                    }
                    return "RUG_ALERT_WITH_BUTTONS"
                
                # Multiple rugs - show first with navigation
                else:
                    # Store rugs in session for navigation
                    self._rug_list = rugs
                    self._rug_index = 0
                    
                    rug = rugs[0]
                    message = monitor._format_rug_message(rug)
                    
                    # Create buttons with Next option
                    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                    buttons = InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("📊 Token Details", callback_data=f"alert_analyze_{rug.network}_{rug.contract}"),
                            InlineKeyboardButton("📱 Socials", callback_data=f"alert_socials_{rug.network}_{rug.contract}")
                        ],
                        [
                            InlineKeyboardButton("🐋 Whale Tracker", callback_data=f"alert_whale_{rug.network}_{rug.contract}"),
                            InlineKeyboardButton("⚖️ BALZ Rank", callback_data=f"alert_balz_{rug.network}_{rug.contract}")
                        ],
                        [
                            InlineKeyboardButton(f"Next → ({len(rugs)-1} more)", callback_data="next_rug")
                        ]
                    ])
                    
                    # Store for async sending
                    self._pending_rug_alert = {
                        'message': message,
                        'buttons': buttons
                    }
                    return "RUG_ALERT_WITH_BUTTONS"
            else:
                return "rug tracker not running yet. they're probably happening tho"
        except Exception as e:
            logger.error(f"Error getting rug summary: {e}")
            return "rug tracker broke. ironic"
        
    def run(self):
        """Start the bot"""
        if not self.application:
            self.setup()
        
        logger.info("Starting BIGBALZ Bot...")
        self.application.run_polling(drop_pending_updates=True)
