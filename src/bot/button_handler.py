"""
Button Handler with Terminal State Design
Manages all button interactions and enforces terminal states
"""

import logging
from typing import Optional, Dict, Any
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from src.classification.reasoning_engine import ReasoningEngine
from src.classification.response_generator import ResponseGenerator
from src.api.whale_tracker import WhaleTracker
from src.database.session_manager import SessionState

logger = logging.getLogger(__name__)


class ButtonHandler:
    """
    Handles all button interactions with terminal state enforcement
    Terminal states: BALZ Rank and Whale Tracker (no further buttons)
    """
    
    def __init__(self, api_client, session_manager, reasoning_engine=None, 
                 response_generator=None, whale_tracker=None, bot_handler=None):
        """
        Initialize button handler
        
        Args:
            api_client: GeckoTerminal API client
            session_manager: Session state manager
            reasoning_engine: BALZ classification engine
            response_generator: Response generator for BALZ
            whale_tracker: Whale analysis system
            bot_handler: Reference to telegram bot handler
        """
        self.api_client = api_client
        self.session_manager = session_manager
        self.reasoning_engine = reasoning_engine or ReasoningEngine()
        self.response_generator = response_generator
        self.whale_tracker = whale_tracker
        self.bot_handler = bot_handler
        
        # Button callback patterns
        self.BUTTON_CALLBACKS = {
            'socials': self.handle_socials_button,
            'balz_rank': self.handle_balz_button,
            'whale_tracker': self.handle_whale_button,
            'refresh_price': self.handle_refresh_button,
            'alert_analyze': self.handle_alert_analyze_button,
            'alert_socials': self.handle_alert_socials_button,
            'alert_whale': self.handle_alert_whale_button,
            'alert_balz': self.handle_alert_balz_button,
            'back_to_alert': self.handle_back_to_alert_button
        }
        
    async def _schedule_message_deletion(self, chat_id: int, message_id: int, deletion_time: int):
        """Schedule message deletion through bot handler"""
        if self.bot_handler:
            # Convert deletion_time (seconds) to absolute timestamp
            import time
            deletion_timestamp = time.time() + deletion_time
            await self.bot_handler._schedule_message_deletion(chat_id, message_id, deletion_timestamp)
        
    def create_token_overview_buttons(self) -> InlineKeyboardMarkup:
        """
        Create the standard 4-button layout for token overview
        
        Returns:
            InlineKeyboardMarkup with 4 buttons
        """
        keyboard = [
            [
                InlineKeyboardButton("📱 Socials", callback_data="socials"),
                InlineKeyboardButton("⚖️ BALZ Rank", callback_data="balz_rank")
            ],
            [
                InlineKeyboardButton("🐋 Whale Tracker", callback_data="whale_tracker"),
                InlineKeyboardButton("🔄 Refresh Price", callback_data="refresh_price")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def create_main_buttons(self, hide_button: Optional[str] = None, show_back: bool = False) -> InlineKeyboardMarkup:
        """
        Create main navigation buttons, hiding the current function's button
        
        Args:
            hide_button: Button to hide (e.g., 'socials', 'balz_rank', etc.)
            show_back: Whether to show "Back to Token Details" button
            
        Returns:
            InlineKeyboardMarkup with appropriate buttons
        """
        buttons = []
        
        # First row of buttons
        first_row = []
        if hide_button != 'socials':
            first_row.append(InlineKeyboardButton("📱 Socials", callback_data="socials"))
        if hide_button != 'balz_rank':
            first_row.append(InlineKeyboardButton("⚖️ BALZ Rank", callback_data="balz_rank"))
        
        if first_row:
            buttons.append(first_row)
        
        # Second row of buttons
        second_row = []
        if hide_button != 'whale_tracker':
            second_row.append(InlineKeyboardButton("🐋 Whale Tracker", callback_data="whale_tracker"))
        
        # Only show refresh button if we're not hiding it AND not showing back button
        if hide_button != 'refresh_price' and not show_back:
            second_row.append(InlineKeyboardButton("🔄 Refresh Price", callback_data="refresh_price"))
        
        if second_row:
            buttons.append(second_row)
        
        # Add "Back to Token Details" button if needed (replaces refresh when in sub-functions)
        if show_back and hide_button and hide_button != 'refresh_price':
            buttons.append([InlineKeyboardButton("🔙 Back to Token Details", callback_data="refresh_price")])
        
        return InlineKeyboardMarkup(buttons)
    
    def create_moonshot_buttons(self, contract: str, network: str) -> InlineKeyboardMarkup:
        """
        Create buttons for moonshot alerts (4 buttons)
        
        Args:
            contract: Contract address
            network: Network identifier
            
        Returns:
            InlineKeyboardMarkup with standard 4 buttons
        """
        # Store contract and network in callback data
        keyboard = [
            [
                InlineKeyboardButton("📊 Token Details", callback_data=f"alert_analyze_{network}_{contract}"),
                InlineKeyboardButton("📱 Socials", callback_data=f"alert_socials_{network}_{contract}")
            ],
            [
                InlineKeyboardButton("🐋 Whale Tracker", callback_data=f"alert_whale_{network}_{contract}"),
                InlineKeyboardButton("⚖️ BALZ Rank", callback_data=f"alert_balz_{network}_{contract}")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def create_token_overview_buttons_with_back(self, network: str, contract: str) -> InlineKeyboardMarkup:
        """
        Create token overview buttons with back to alert option
        
        Args:
            network: Network identifier
            contract: Contract address
            
        Returns:
            InlineKeyboardMarkup with 4 buttons + back
        """
        keyboard = [
            [
                InlineKeyboardButton("📱 Socials", callback_data="socials"),
                InlineKeyboardButton("⚖️ BALZ Rank", callback_data="balz_rank")
            ],
            [
                InlineKeyboardButton("🐋 Whale Tracker", callback_data="whale_tracker"),
                InlineKeyboardButton("🔄 Refresh Price", callback_data="refresh_price")
            ],
            [
                InlineKeyboardButton("🔙 Back to Alert", callback_data=f"back_to_alert_{network}_{contract}")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def handle_button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Main button callback handler
        Routes button presses to appropriate handlers
        
        Args:
            update: Telegram update object
            context: Callback context
        """
        query = update.callback_query
        await query.answer()  # Acknowledge the button press
        
        callback_data = query.data
        chat_id = query.message.chat_id
        user_id = query.from_user.id
        
        # Check if this is a private chat
        if query.message.chat.type == 'private':
            ALLOWED_DM_USERS = [831955563]
            
            if user_id not in ALLOWED_DM_USERS:
                await query.message.reply_text(
                    "clicking buttons in my DMs? that's weird bro\n\njoin @MUSKYBALZAC if you wanna play with buttons"
                )
                return
        
        logger.info(f"Button pressed: {callback_data} by user {user_id}")
        
        # Handle alert buttons (from moonshot/rug alerts)
        if callback_data.startswith('alert_'):
            parts = callback_data.split('_')
            if len(parts) >= 4:
                action = parts[1]  # analyze, socials, whale, balz
                network = parts[2]
                contract = '_'.join(parts[3:])
                
                session = self.session_manager.get_session(chat_id, 0)  # Use 0 for broadcast user_id
                if not session:
                    session = self.session_manager.create_session(
                        chat_id=chat_id,
                        user_id=0,
                        token_name="Alert Token",
                        contract=contract,
                        network=network,
                        token_data={}
                    )
                
                session.alert_context = {
                    'contract': contract,
                    'network': network,
                    'symbol': 'Alert Token'  # Will be updated when token data is fetched
                }
                
                # Route to appropriate alert handler
                if action == 'analyze':
                    await self.handle_alert_analyze_button(query, callback_data)
                elif action == 'socials':
                    await self.handle_alert_socials_button(query, callback_data)
                elif action == 'whale':
                    await self.handle_alert_whale_button(query, callback_data)
                elif action == 'balz':
                    await self.handle_alert_balz_button(query, callback_data)
                else:
                    await query.edit_message_text("❌ Unknown alert action.")
                    deletion_time = 25 * 60
                    await self._schedule_message_deletion(query.message.chat_id, query.message.message_id, deletion_time)
            else:
                await query.edit_message_text("❌ Invalid alert button data.")
                deletion_time = 25 * 60
                await self._schedule_message_deletion(query.message.chat_id, query.message.message_id, deletion_time)
            return
        
        # Handle back to alert button
        if callback_data.startswith('back_to_alert_'):
            await self._handle_back_to_alert(query, callback_data)
            return
        
        # Handle gem research flow
        if callback_data.startswith('choice_'):
            await self._handle_gem_choice(query, callback_data)
            return
        elif callback_data.startswith('gem_network_'):
            await self._handle_gem_network_selection(query, callback_data)
            return
        elif callback_data.startswith('gem_age_'):
            await self._handle_gem_age_selection(query, callback_data)
            return
        elif callback_data.startswith('gem_liq_'):
            await self._handle_gem_liquidity_selection(query, callback_data)
            return
        elif callback_data.startswith('gem_mcap_'):
            await self._handle_gem_mcap_selection(query, callback_data)
            return
        elif callback_data.startswith('gem_analyze_'):
            await self._handle_gem_analyze(query, callback_data)
            return
        elif callback_data.startswith('gem_socials_'):
            await self._handle_gem_socials(query, callback_data)
            return
        elif callback_data.startswith('gem_whale_'):
            await self._handle_gem_whale(query, callback_data)
            return
        elif callback_data.startswith('gem_balz_'):
            await self._handle_gem_balz(query, callback_data)
            return
        elif callback_data.startswith('gem_next_'):
            await self._handle_gem_navigation(query, callback_data, 'next')
            return
        elif callback_data.startswith('gem_back_'):
            await self._handle_gem_navigation(query, callback_data, 'back')
            return
        elif callback_data.startswith('back_to_gem_'):
            await self._handle_back_to_gem(query, callback_data)
            return
        
        # Handle moonshot/rug navigation
        if callback_data == 'next_moonshot':
            await self._handle_next_moonshot(query)
            return
        elif callback_data == 'prev_moonshot':
            await self._handle_prev_moonshot(query)
            return
        elif callback_data == 'next_rug':
            await self._handle_next_rug(query)
            return
        elif callback_data == 'prev_rug':
            await self._handle_prev_rug(query)
            return
        elif callback_data == 'view_moonshots':
            await self._handle_view_moonshots(query)
            return
        elif callback_data == 'view_rugs':
            await self._handle_view_rugs(query)
            return
        
        # Get session data
        session = self.session_manager.get_session(chat_id, user_id)
        if not session or not session.current_contract:
            await query.edit_message_text(
                "⏰ Session expired. Please send a new contract address.",
                parse_mode='Markdown'
            )
            deletion_time = 25 * 60
            await self._schedule_message_deletion(query.message.chat_id, query.message.message_id, deletion_time)
            return
        
        # Route to appropriate handler
        handler = self.BUTTON_CALLBACKS.get(callback_data)
        if handler:
            try:
                await handler(query, session)
            except Exception as e:
                logger.error(f"Error handling button {callback_data}: {e}")
                await query.edit_message_text(
                    "❌ An error occurred. Please try again.",
                    parse_mode='Markdown'
                )
                deletion_time = 25 * 60
                await self._schedule_message_deletion(query.message.chat_id, query.message.message_id, deletion_time)
        else:
            await query.edit_message_text("Unknown button action.")
            deletion_time = 25 * 60
            await self._schedule_message_deletion(query.message.chat_id, query.message.message_id, deletion_time)
    
    async def handle_socials_button(self, query, session: SessionState):
        """
        Handle socials button press
        Shows social links and project info with 2 terminal buttons
        """
        try:
            # Show loading message
            await query.edit_message_text("🔍 Fetching social information...")
            
            # API call for social information
            social_data = await self.api_client.get_social_info(
                session.current_network,
                session.current_contract
            )
            
            if social_data:
                response = self._format_social_response(social_data, session.current_token)
                buttons = self.create_main_buttons(hide_button='socials', show_back=True)
                
                await query.edit_message_text(
                    response,
                    reply_markup=buttons,
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
                deletion_time = 25 * 60
                await self._schedule_message_deletion(query.message.chat_id, query.message.message_id, deletion_time)
            else:
                buttons = self.create_main_buttons(hide_button='socials', show_back=True)
                await query.edit_message_text(
                    f"📱 **Social Links for {session.current_token}**\n\n"
                    "ℹ️ No social information available for this token.\n\n"
                    "This could mean:\n"
                    "• The project hasn't set up social profiles\n"
                    "• The token is too new\n"
                    "• It might be a scam token\n\n"
                    "⚠️ Be extra cautious with tokens that have no social presence!",
                    reply_markup=buttons,
                    parse_mode='Markdown'
                )
                deletion_time = 25 * 60
                await self._schedule_message_deletion(query.message.chat_id, query.message.message_id, deletion_time)
        except Exception as e:
            logger.error(f"Error fetching social data: {e}")
            await query.edit_message_text(
                "❌ Error fetching social data. Please try again later.",
                parse_mode='Markdown'
            )
            deletion_time = 25 * 60
            await self._schedule_message_deletion(query.message.chat_id, query.message.message_id, deletion_time)
    
    async def handle_balz_button(self, query, session: SessionState):
        """
        Handle BALZ rank button press - TERMINAL STATE
        Shows complete BALZ classification with no further buttons
        """
        try:
            # Show loading message
            await query.edit_message_text("⚖️ Analyzing BALZ classification...")
            
            # Use cached token data for classification
            token_data = session.token_data
            if not token_data:
                await query.edit_message_text(
                    "❌ Token data not available. Please refresh and try again.",
                    parse_mode='Markdown'
                )
                return
            
            # Reconstruct TokenData object from dict if needed
            from ..api.geckoterminal_client import TokenData
            if isinstance(token_data, dict):
                # Create TokenData from dict
                token_obj = TokenData(
                    symbol=token_data.get('symbol', 'UNKNOWN'),
                    name=token_data.get('name', 'Unknown'),
                    contract_address=token_data.get('contract_address', ''),
                    network=token_data.get('network', ''),
                    price_usd=token_data.get('price_usd', 0),
                    market_cap_usd=token_data.get('market_cap_usd', 0),
                    fdv_usd=token_data.get('fdv_usd', 0),
                    volume_24h=token_data.get('volume_24h', 0),
                    total_supply=token_data.get('total_supply', '0'),
                    liquidity_usd=token_data.get('liquidity_usd', 0),
                    primary_dex=token_data.get('primary_dex', 'Unknown'),
                    price_change_24h=token_data.get('price_change_24h', 0),
                    price_change_1h=token_data.get('price_change_1h', 0),
                    price_change_5m=token_data.get('price_change_5m', 0),
                    pool_address=token_data.get('pool_address')
                )
                token_data = token_obj
            
            # Classify token
            classification = self.reasoning_engine.classify_token(token_data)
            
            # Generate response
            if self.response_generator:
                response = await self.response_generator.generate_balz_response(
                    classification, token_data
                )
            else:
                # Fallback response if no OpenAI
                response = self._generate_fallback_balz_response(classification, token_data)
            
            # Show buttons with BALZ Rank hidden
            buttons = self.create_main_buttons(hide_button='balz_rank', show_back=True)
            await query.edit_message_text(response, reply_markup=buttons, parse_mode='Markdown')
            
            deletion_time = 25 * 60
            await self._schedule_message_deletion(query.message.chat_id, query.message.message_id, deletion_time)
            
            logger.info(f"BALZ classification complete: {classification.category.value} for {session.current_token}")
            
        except Exception as e:
            logger.error(f"Error generating BALZ analysis: {e}")
            await query.edit_message_text(
                "❌ Error generating BALZ analysis. Please try again.",
                parse_mode='Markdown'
            )
    
    async def handle_whale_button(self, query, session: SessionState):
        """
        Handle whale tracker button press - TERMINAL STATE
        Shows whale analysis with no further buttons
        """
        try:
            # Show loading message
            await query.edit_message_text("🐋 Analyzing whale activity...")
            
            if self.whale_tracker:
                # Get whale analysis
                whale_data = await self.whale_tracker.analyze_whales(
                    session.current_network,
                    session.current_contract,
                    session.token_data
                )
                
                if whale_data:
                    response = self.whale_tracker.format_whale_response(
                        whale_data, session.current_token
                    )
                else:
                    response = (
                        f"🐋 **Whale Tracker: {session.current_token}**\n\n"
                        "❌ Unable to analyze whale activity.\n\n"
                        "This could mean:\n"
                        "• No recent large transactions\n"
                        "• Limited trading history\n"
                        "• Data temporarily unavailable\n\n"
                        "Try again later for updated analysis."
                    )
            else:
                response = (
                    f"🐋 **Whale Tracker: {session.current_token}**\n\n"
                    "⚠️ Whale tracking system is currently unavailable.\n"
                    "Please try again later."
                )
            
            # Show buttons with Whale Tracker hidden
            buttons = self.create_main_buttons(hide_button='whale_tracker', show_back=True)
            await query.edit_message_text(response, reply_markup=buttons, parse_mode='Markdown')
            
            deletion_time = 25 * 60
            await self._schedule_message_deletion(query.message.chat_id, query.message.message_id, deletion_time)
            
        except Exception as e:
            logger.error(f"Error in whale analysis: {e}")
            await query.edit_message_text(
                "❌ Error analyzing whale activity. Please try again.",
                parse_mode='Markdown'
            )
    
    async def handle_refresh_button(self, query, session: SessionState):
        """
        Handle refresh price button press
        Fetches fresh data and shows token overview with all 4 buttons
        """
        try:
            # Show loading message
            await query.edit_message_text("🔄 Refreshing token data...")
            
            # Fetch fresh token data
            token_data = await self.api_client.get_token_info(
                session.current_network,
                session.current_contract,
                priority=0  # High priority for user request
            )
            
            if not token_data:
                await query.edit_message_text(
                    "❌ Unable to refresh token data. Please try again.",
                    parse_mode='Markdown'
                )
                return
            
            # Update session with fresh data
            self.session_manager.update_token_data(
                session.chat_id,
                session.user_id,
                token_data.to_dict()
            )
            
            # Format updated overview
            from ..bot.message_formatter import MessageFormatter
            overview_message = MessageFormatter.format_token_overview(token_data)
            
            # Create buttons (all 4 buttons - reset cycle)
            buttons = self.create_token_overview_buttons()
            
            # Show updated data with buttons
            await query.edit_message_text(
                overview_message,
                reply_markup=buttons,
                parse_mode='Markdown'
            )
            
            logger.info(f"Refreshed data for {token_data.symbol}")
            
        except Exception as e:
            logger.error(f"Error refreshing token data: {e}")
            await query.edit_message_text(
                "❌ Error refreshing data. Please try again.",
                parse_mode='Markdown'
            )
    
    async def _handle_alert_button(self, query, callback_data: str):
        """
        Legacy alert button handler - now deprecated
        Alert buttons are routed directly to dedicated handlers in handle_button_callback
        """
        await query.edit_message_text(
            "❌ Legacy alert handler called. Please try again.",
            parse_mode='Markdown'
        )
        deletion_time = 25 * 60
        await self._schedule_message_deletion(query.message.chat_id, query.message.message_id, deletion_time)
    
    async def _handle_back_to_alert(self, query, callback_data: str):
        """
        Handle back to alert button - recreates original alert view
        """
        parts = callback_data.split('_')
        if len(parts) < 5:
            await query.edit_message_text("Invalid button data.")
            return
        
        network = parts[3]
        contract = '_'.join(parts[4:])
        
        # Try to find the alert in background monitor's history
        if self.bot_handler and self.bot_handler.background_monitor:
            monitor = self.bot_handler.background_monitor
            
            # Check if it's a moonshot
            moonshot_alert = monitor.detected_moonshots.get(contract)
            if moonshot_alert:
                # Recreate moonshot alert message
                message = monitor._format_moonshot_message(moonshot_alert)
                buttons = self.create_moonshot_buttons(contract, network)
                await query.edit_message_text(
                    message,
                    reply_markup=buttons,
                    parse_mode='Markdown'
                )
                return
            
            # Check if it's a rug
            rug_alert = monitor.detected_rugs.get(contract)
            if rug_alert:
                # Recreate rug alert message
                message = monitor._format_rug_message(rug_alert)
                buttons = self.create_moonshot_buttons(contract, network)  # Same buttons for rugs
                await query.edit_message_text(
                    message,
                    reply_markup=buttons,
                    parse_mode='Markdown'
                )
                return
        
        # Fallback to generic message if alert not found
        alert_message = f"📊 **Token Alert**\n\n📱 **Contract:** `{contract}`\n\n🌐 **Network:** {network.upper()}\n\n_Alert details not available. Select an option below:_"
        
        buttons = self.create_moonshot_buttons(contract, network)
        
        await query.edit_message_text(
            alert_message,
            reply_markup=buttons,
            parse_mode='Markdown'
        )
    
    def _format_social_response(self, social_data, token_name: str) -> str:
        """Format social links response"""
        response = f"📱 **Social Links for {token_name}**\n\n"
        
        # Add description if available
        if social_data.description:
            description = social_data.description[:300]
            if len(social_data.description) > 300:
                description += "..."
            response += f"📄 **Description:** {description}\n\n"
        
        # Add social links
        social_links = []
        
        if social_data.websites:
            for i, website in enumerate(social_data.websites[:2]):  # Limit to 2
                social_links.append(f"🌐 [Website {i+1}]({website})")
        
        if social_data.twitter_handle:
            social_links.append(f"🐦 [Twitter](https://twitter.com/{social_data.twitter_handle})")
        
        if social_data.telegram_handle:
            social_links.append(f"📱 [Telegram](https://t.me/{social_data.telegram_handle})")
        
        if social_data.discord_url:
            social_links.append(f"💬 [Discord]({social_data.discord_url})")
        
        if social_links:
            response += "🔗 **Links:**\n" + "\n".join(social_links)
        else:
            response += "ℹ️ No social links available for this token."
        
        if social_data.coingecko_coin_id:
            response += f"\n\n📊 [View on CoinGecko](https://www.coingecko.com/en/coins/{social_data.coingecko_coin_id})"
        
        return response
    
    def _get_random_savage_line(self) -> str:
        """Get random savage closing line"""
        savage_lines = [
            "Don't cry at the casino! 🎰",
            "This is not financial advice! 🚫",
            "Ape at your own risk! 🦍",
            "Welcome to the trenches! ⚰️",
            "May the gains be with you! 💸",
            "WAGMI or NGMI - your choice! 🎲",
            "Remember: scared money don't make money! 💵"
        ]
        import random
        return random.choice(savage_lines)
    
    async def _handle_next_moonshot(self, query):
        """Handle next moonshot navigation"""
        if not self.bot_handler or not hasattr(self.bot_handler, '_moonshot_list'):
            await query.edit_message_text("Moonshot list expired. Ask 'any moonshots?' again.")
            return
        
        # Increment index
        self.bot_handler._moonshot_index = (self.bot_handler._moonshot_index + 1) % len(self.bot_handler._moonshot_list)
        moonshot = self.bot_handler._moonshot_list[self.bot_handler._moonshot_index]
        
        # Format message
        message = self.bot_handler.background_monitor._format_moonshot_message(moonshot)
        
        # Create buttons
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        buttons = [
            [
                InlineKeyboardButton("📊 Token Details", callback_data=f"alert_analyze_{moonshot.network}_{moonshot.contract}"),
                InlineKeyboardButton("📱 Socials", callback_data=f"alert_socials_{moonshot.network}_{moonshot.contract}")
            ],
            [
                InlineKeyboardButton("🐋 Whale Tracker", callback_data=f"alert_whale_{moonshot.network}_{moonshot.contract}"),
                InlineKeyboardButton("⚖️ BALZ Rank", callback_data=f"alert_balz_{moonshot.network}_{moonshot.contract}")
            ]
        ]
        
        # Add navigation buttons
        nav_buttons = []
        total = len(self.bot_handler._moonshot_list)
        current = self.bot_handler._moonshot_index
        
        # Add Back button if not at start
        if current > 0:
            nav_buttons.append(InlineKeyboardButton("← Back", callback_data="prev_moonshot"))
        
        # Add Next button if not at end
        if current < total - 1:
            remaining = total - current - 1
            nav_buttons.append(InlineKeyboardButton(f"Next → ({remaining} more)", callback_data="next_moonshot"))
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
        deletion_time = 25 * 60
        await self._schedule_message_deletion(query.message.chat_id, query.message.message_id, deletion_time)
    
    async def _handle_prev_moonshot(self, query):
        """Handle previous moonshot navigation"""
        if not self.bot_handler or not hasattr(self.bot_handler, '_moonshot_list'):
            await query.edit_message_text("Moonshot list expired. Ask 'any moonshots?' again.")
            return
        
        # Decrement index
        self.bot_handler._moonshot_index = (self.bot_handler._moonshot_index - 1) % len(self.bot_handler._moonshot_list)
        moonshot = self.bot_handler._moonshot_list[self.bot_handler._moonshot_index]
        
        # Format message
        message = self.bot_handler.background_monitor._format_moonshot_message(moonshot)
        
        # Create buttons
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        buttons = [
            [
                InlineKeyboardButton("📊 Token Details", callback_data=f"alert_analyze_{moonshot.network}_{moonshot.contract}"),
                InlineKeyboardButton("📱 Socials", callback_data=f"alert_socials_{moonshot.network}_{moonshot.contract}")
            ],
            [
                InlineKeyboardButton("🐋 Whale Tracker", callback_data=f"alert_whale_{moonshot.network}_{moonshot.contract}"),
                InlineKeyboardButton("⚖️ BALZ Rank", callback_data=f"alert_balz_{moonshot.network}_{moonshot.contract}")
            ]
        ]
        
        # Add navigation buttons
        nav_buttons = []
        total = len(self.bot_handler._moonshot_list)
        current = self.bot_handler._moonshot_index
        
        # Add Back button if not at start
        if current > 0:
            nav_buttons.append(InlineKeyboardButton("← Back", callback_data="prev_moonshot"))
        
        # Add Next button if not at end
        if current < total - 1:
            remaining = total - current - 1
            nav_buttons.append(InlineKeyboardButton(f"Next → ({remaining} more)", callback_data="next_moonshot"))
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
        deletion_time = 25 * 60
        await self._schedule_message_deletion(query.message.chat_id, query.message.message_id, deletion_time)
    
    async def _handle_next_rug(self, query):
        """Handle next rug navigation"""
        if not self.bot_handler or not hasattr(self.bot_handler, '_rug_list'):
            await query.edit_message_text("Rug list expired. Ask 'any rugs?' again.")
            return
        
        # Increment index
        self.bot_handler._rug_index = (self.bot_handler._rug_index + 1) % len(self.bot_handler._rug_list)
        rug = self.bot_handler._rug_list[self.bot_handler._rug_index]
        
        # Format message
        message = self.bot_handler.background_monitor._format_rug_message(rug)
        
        # Create buttons
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        buttons = [
            [
                InlineKeyboardButton("📊 Token Details", callback_data=f"alert_analyze_{rug.network}_{rug.contract}"),
                InlineKeyboardButton("📱 Socials", callback_data=f"alert_socials_{rug.network}_{rug.contract}")
            ],
            [
                InlineKeyboardButton("🐋 Whale Tracker", callback_data=f"alert_whale_{rug.network}_{rug.contract}"),
                InlineKeyboardButton("⚖️ BALZ Rank", callback_data=f"alert_balz_{rug.network}_{rug.contract}")
            ]
        ]
        
        # Add navigation buttons
        nav_buttons = []
        total = len(self.bot_handler._rug_list)
        current = self.bot_handler._rug_index
        
        # Add Back button if not at start
        if current > 0:
            nav_buttons.append(InlineKeyboardButton("← Back", callback_data="prev_rug"))
        
        # Add Next button if not at end
        if current < total - 1:
            remaining = total - current - 1
            nav_buttons.append(InlineKeyboardButton(f"Next → ({remaining} more)", callback_data="next_rug"))
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
        deletion_time = 25 * 60
        await self._schedule_message_deletion(query.message.chat_id, query.message.message_id, deletion_time)
    
    async def _handle_prev_rug(self, query):
        """Handle previous rug navigation"""
        if not self.bot_handler or not hasattr(self.bot_handler, '_rug_list'):
            await query.edit_message_text("Rug list expired. Ask 'any rugs?' again.")
            return
        
        # Decrement index
        self.bot_handler._rug_index = (self.bot_handler._rug_index - 1) % len(self.bot_handler._rug_list)
        rug = self.bot_handler._rug_list[self.bot_handler._rug_index]
        
        # Format message
        message = self.bot_handler.background_monitor._format_rug_message(rug)
        
        # Create buttons
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        buttons = [
            [
                InlineKeyboardButton("📊 Token Details", callback_data=f"alert_analyze_{rug.network}_{rug.contract}"),
                InlineKeyboardButton("📱 Socials", callback_data=f"alert_socials_{rug.network}_{rug.contract}")
            ],
            [
                InlineKeyboardButton("🐋 Whale Tracker", callback_data=f"alert_whale_{rug.network}_{rug.contract}"),
                InlineKeyboardButton("⚖️ BALZ Rank", callback_data=f"alert_balz_{rug.network}_{rug.contract}")
            ]
        ]
        
        # Add navigation buttons
        nav_buttons = []
        total = len(self.bot_handler._rug_list)
        current = self.bot_handler._rug_index
        
        # Add Back button if not at start
        if current > 0:
            nav_buttons.append(InlineKeyboardButton("← Back", callback_data="prev_rug"))
        
        # Add Next button if not at end
        if current < total - 1:
            remaining = total - current - 1
            nav_buttons.append(InlineKeyboardButton(f"Next → ({remaining} more)", callback_data="next_rug"))
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
        deletion_time = 25 * 60
        await self._schedule_message_deletion(query.message.chat_id, query.message.message_id, deletion_time)
    
    async def _handle_view_moonshots(self, query):
        """Handle view moonshots from status report"""
        try:
            if not self.bot_handler or not self.bot_handler.background_monitor:
                await query.edit_message_text("Background monitor not available")
                return
            
            import time
            monitor = self.bot_handler.background_monitor
            cutoff_time = time.time() - (45 * 60)  # Last 45 minutes
            
            # Get recent moonshots
            moonshots = []
            for contract, moonshot_alert in monitor.detected_moonshots.items():
                if moonshot_alert.timestamp.timestamp() >= cutoff_time:
                    moonshots.append(moonshot_alert)
            
            if not moonshots:
                await query.edit_message_text("📈 **Recent Moonshots (45 min)**\n\nNo moonshots detected in the last 45 minutes.")
                return
            
            # Sort by timestamp (newest first)
            moonshots.sort(key=lambda x: x.timestamp, reverse=True)
            
            # Network names
            network_names = {
                'eth': 'Ethereum',
                'solana': 'Solana',
                'bsc': 'BNB Smart Chain',
                'base': 'Base'
            }
            
            # Tier emojis
            tier_emojis = {
                'POTENTIAL 100X': '🚀',
                'POTENTIAL 10X': '⚡',
                'POTENTIAL 2X': '💰'
            }
            
            message = f"📈 **Recent Moonshots (45 min)**\n\nFound {len(moonshots)} moonshots:\n\n"
            
            for i, moonshot in enumerate(moonshots[:10], 1):  # Show max 10
                emoji = tier_emojis.get(moonshot.tier, '🌟')
                network_display = network_names.get(moonshot.network, moonshot.network.upper())
                
                message += f"{i}. {emoji} **{moonshot.token_symbol}** ({moonshot.tier})\n"
                message += f"   Network: {network_display}\n"
                message += f"   Contract: `{moonshot.contract}`\n"
                message += f"   Change: +{moonshot.price_change_percent:.1f}%\n"
                message += f"   Liquidity: ${moonshot.liquidity:,.0f}\n\n"
            
            if len(moonshots) > 10:
                message += f"...and {len(moonshots) - 10} more\n\n"
            
            message += "_Click 'any moonshots?' for full alerts with buttons_"
            
            await query.edit_message_text(
                message,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error viewing moonshots: {e}")
            await query.edit_message_text("Error loading moonshots")
    
    async def _handle_view_rugs(self, query):
        """Handle view rugs from status report"""
        try:
            if not self.bot_handler or not self.bot_handler.background_monitor:
                await query.edit_message_text("Background monitor not available")
                return
            
            import time
            monitor = self.bot_handler.background_monitor
            cutoff_time = time.time() - (45 * 60)  # Last 45 minutes
            
            # Get recent rugs
            rugs = []
            for contract, rug_alert in monitor.detected_rugs.items():
                if rug_alert.timestamp.timestamp() >= cutoff_time:
                    rugs.append(rug_alert)
            
            if not rugs:
                await query.edit_message_text("💀 **Recent Rugs (45 min)**\n\nNo rugs detected in the last 45 minutes. Surprisingly peaceful!")
                return
            
            # Sort by timestamp (newest first)
            rugs.sort(key=lambda x: x.timestamp, reverse=True)
            
            # Network names
            network_names = {
                'eth': 'Ethereum',
                'solana': 'Solana',
                'bsc': 'BNB Smart Chain',
                'base': 'Base'
            }
            
            # Severity emojis
            severity_emojis = {
                "REKT TO OBLIVION": "💀",
                "LIQUIDITY EXTRACTION": "☠️",
                "SOFT RUG": "🔥"
            }
            
            message = f"💀 **Recent Rugs (45 min)**\n\nCaught {len(rugs)} rugs:\n\n"
            
            for i, rug in enumerate(rugs[:10], 1):  # Show max 10
                network_display = network_names.get(rug.network, rug.network.upper())
                emoji = severity_emojis.get(getattr(rug, 'severity_level', ''), "💀")
                severity = getattr(rug, 'severity_level', 'RUG')
                
                message += f"{i}. {emoji} **{rug.token_symbol}** ({severity})\n"
                message += f"   Network: {network_display}\n"
                message += f"   Contract: `{rug.contract}`\n"
                
                # Show the damage
                if rug.liquidity_drain_percent > rug.price_drop_percent:
                    message += f"   Liquidity drained: -{rug.liquidity_drain_percent:.0f}%\n"
                else:
                    message += f"   Price nuked: -{rug.price_drop_percent:.0f}%\n"
                
                message += f"   Final liquidity: ${rug.final_liquidity:,.0f}\n\n"
            
            if len(rugs) > 10:
                message += f"...and {len(rugs) - 10} more corpses\n\n"
            
            message += "_Click 'any rugs?' for full alerts with buttons_"
            
            await query.edit_message_text(
                message,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error viewing rugs: {e}")
            await query.edit_message_text("Error loading rugs")
    
    async def _handle_gem_choice(self, query, callback_data: str):
        """Handle initial choice between moonshots and gem research"""
        chat_id = query.message.chat_id
        user_id = query.from_user.id
        message_id = query.message.message_id
        
        if callback_data == 'choice_moonshots':
            # Handle existing moonshot logic
            if self.bot_handler:
                response = self.bot_handler._get_moonshot_summary()
                if response == "MOONSHOT_ALERT_WITH_BUTTONS":
                    alert_data = self.bot_handler._pending_moonshot_alert
                    await query.edit_message_text(
                        alert_data['message'],
                        parse_mode='Markdown',
                        reply_markup=alert_data['buttons']
                    )
                    self.bot_handler._pending_moonshot_alert = None
                    # Schedule deletion for moonshot buttons
                    deletion_time = 25 * 60  # 25 minutes
                    await self._schedule_message_deletion(chat_id, message_id, deletion_time)
                else:
                    await query.edit_message_text(response)
        
        elif callback_data == 'choice_gems':
            # Start gem research flow
            if hasattr(self.bot_handler, 'gem_research_handler'):
                gem_handler = self.bot_handler.gem_research_handler
                gem_handler.create_or_get_session(chat_id, user_id)
                
                message, buttons = gem_handler.get_network_selection_message()
                await query.edit_message_text(
                    message,
                    parse_mode='Markdown', 
                    reply_markup=buttons
                )
                # Schedule deletion for gem research buttons
                deletion_time = 25 * 60  # 25 minutes
                await self._schedule_message_deletion(chat_id, message_id, deletion_time)
    
    async def _handle_gem_network_selection(self, query, callback_data: str):
        """Handle network selection in gem research"""
        chat_id = query.message.chat_id
        user_id = query.from_user.id
        message_id = query.message.message_id
        
        network_map = {
            'gem_network_solana': 'solana',
            'gem_network_eth': 'eth',
            'gem_network_bsc': 'bsc', 
            'gem_network_base': 'base'
        }
        
        network = network_map.get(callback_data)
        if not network:
            return
        
        gem_handler = self.bot_handler.gem_research_handler
        gem_handler.update_session_step(chat_id, user_id, 'age', network=network)
        
        message, buttons = gem_handler.get_age_selection_message()
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=buttons
        )
        # Schedule deletion
        deletion_time = 25 * 60  # 25 minutes
        await self._schedule_message_deletion(chat_id, message_id, deletion_time)
    
    async def _handle_gem_age_selection(self, query, callback_data: str):
        """Handle age selection in gem research"""
        chat_id = query.message.chat_id
        user_id = query.from_user.id
        message_id = query.message.message_id
        
        age_map = {
            'gem_age_last48': 'last_48',
            'gem_age_older2days': 'older_2_days'
        }
        
        age = age_map.get(callback_data)
        if not age:
            return
        
        gem_handler = self.bot_handler.gem_research_handler
        session = gem_handler.create_or_get_session(chat_id, user_id)
        await gem_handler.handle_age_selection(session, age)
        gem_handler.update_session_step(chat_id, user_id, 'liquidity', age=age)
        
        message, buttons = gem_handler.get_liquidity_selection_message()
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=buttons
        )
        # Schedule deletion
        deletion_time = 25 * 60  # 25 minutes
        await self._schedule_message_deletion(chat_id, message_id, deletion_time)
    
    async def _handle_gem_liquidity_selection(self, query, callback_data: str):
        """Handle liquidity selection in gem research"""
        chat_id = query.message.chat_id
        user_id = query.from_user.id
        message_id = query.message.message_id
        
        liq_map = {
            'gem_liq_10_50': '10_50',
            'gem_liq_50_250': '50_250',
            'gem_liq_250_1000': '250_1000',
            'gem_liq_1000_plus': '1000_plus'
        }
        
        liquidity = liq_map.get(callback_data)
        if not liquidity:
            return
        
        gem_handler = self.bot_handler.gem_research_handler
        gem_handler.update_session_step(chat_id, user_id, 'mcap', liquidity=liquidity)
        
        message, buttons = gem_handler.get_mcap_selection_message()
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=buttons
        )
        # Schedule deletion
        deletion_time = 25 * 60  # 25 minutes
        await self._schedule_message_deletion(chat_id, message_id, deletion_time)
    
    async def _handle_gem_mcap_selection(self, query, callback_data: str):
        """Handle market cap selection and execute research"""
        chat_id = query.message.chat_id
        user_id = query.from_user.id
        message_id = query.message.message_id
        
        mcap_map = {
            'gem_mcap_micro': 'micro',
            'gem_mcap_small': 'small',
            'gem_mcap_mid': 'mid'
        }
        
        mcap = mcap_map.get(callback_data)
        if not mcap:
            return
        
        gem_handler = self.bot_handler.gem_research_handler
        session = gem_handler.create_or_get_session(chat_id, user_id)
        session.criteria.mcap = mcap
        session.step = 'results'
        
        # Show loading message
        loading_message = gem_handler.get_research_loading_message(session.criteria)
        await query.edit_message_text(loading_message, parse_mode='Markdown')
        
        # Execute research
        gems = await gem_handler.execute_gem_research(session)
        
        if not gems:
            # No gems found
            message, buttons = gem_handler.get_no_gems_message(session.criteria.network)
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=buttons
            )
            # Schedule deletion for no gems found state
            deletion_time = 25 * 60  # 25 minutes
            await self._schedule_message_deletion(chat_id, message_id, deletion_time)
        else:
            # Store results and show first gem
            session.results = gems
            session.current_index = 0
            
            message, buttons = gem_handler.format_single_gem_result_from_pool(
                gems[0], session.criteria, 0, len(gems)
            )
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=buttons
            )
            # Schedule deletion for gem result state
            deletion_time = 25 * 60  # 25 minutes
            await self._schedule_message_deletion(chat_id, message_id, deletion_time)
    
    async def _handle_gem_analyze(self, query, callback_data: str):
        """Handle gem token details analysis"""
        chat_id = query.message.chat_id
        message_id = query.message.message_id
        user_id = query.from_user.id
        
        parts = callback_data.split('_')
        if len(parts) < 4:
            return
        
        network = parts[2]
        contract = '_'.join(parts[3:])
        
        session = self.session_manager.get_session(chat_id, user_id)
        if not session:
            session = self.session_manager.create_session(chat_id, user_id, "Gem", contract, network, {})
        
        # Store in session for consistent access pattern
        session.current_contract = contract
        session.current_network = network
        
        # Get token data using session properties
        token_data = await self.api_client.get_token_info(session.current_network, session.current_contract)
        if not token_data:
            await query.edit_message_text("❌ Unable to fetch token data")
            return
        
        session.current_token = token_data.symbol
        session.current_token_data = token_data
        
        # Format token overview
        from ..bot.message_formatter import MessageFormatter
        overview = MessageFormatter.format_token_overview(token_data)
        
        # Create back button
        gem_handler = self.bot_handler.gem_research_handler
        buttons = gem_handler.create_gem_detail_back_button(0)
        
        await query.edit_message_text(
            overview,
            parse_mode='Markdown',
            reply_markup=buttons
        )
        # Schedule deletion
        deletion_time = 25 * 60  # 25 minutes
        await self._schedule_message_deletion(chat_id, message_id, deletion_time)
    
    async def _handle_gem_socials(self, query, callback_data: str):
        """Handle gem socials"""
        chat_id = query.message.chat_id
        message_id = query.message.message_id
        user_id = query.from_user.id
        
        parts = callback_data.split('_')
        if len(parts) < 4:
            return
        
        network = parts[2]
        contract = '_'.join(parts[3:])
        
        # Get or create session for consistent access pattern
        session = self.session_manager.get_session(chat_id, user_id)
        if not session:
            session = self.session_manager.create_session(chat_id, user_id, "Gem", contract, network, {})
        
        # Store in session for consistent access pattern
        session.current_contract = contract
        session.current_network = network
        
        # Get social data using session properties
        social_data = await self.api_client.get_social_info(session.current_network, session.current_contract)
        
        if social_data:
            # Get token info for name using session properties
            token_data = await self.api_client.get_token_info(session.current_network, session.current_contract)
            if token_data:
                session.current_token = token_data.symbol
                session.current_token_data = token_data
                token_name = f"{token_data.name} ({token_data.symbol})"
            else:
                token_name = "Token"
            
            response = self._format_social_response(social_data, token_name)
        else:
            response = f"📱 **Social Links**\n\nℹ️ No social information available for this token."
        
        # Create back button
        gem_handler = self.bot_handler.gem_research_handler
        buttons = gem_handler.create_gem_detail_back_button(0)
        
        await query.edit_message_text(
            response,
            parse_mode='Markdown',
            reply_markup=buttons
        )
        # Schedule deletion
        deletion_time = 25 * 60  # 25 minutes
        await self._schedule_message_deletion(chat_id, message_id, deletion_time)
    
    async def _handle_gem_whale(self, query, callback_data: str):
        """Handle gem whale tracker"""
        chat_id = query.message.chat_id
        message_id = query.message.message_id
        
        gem_handler = self.bot_handler.gem_research_handler
        message, buttons = gem_handler.format_whale_tracker_message("Token")
        
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=buttons
        )
        # Schedule deletion
        deletion_time = 25 * 60  # 25 minutes
        await self._schedule_message_deletion(chat_id, message_id, deletion_time)
    
    async def _handle_gem_balz(self, query, callback_data: str):
        """Handle gem BALZ rank"""
        chat_id = query.message.chat_id
        message_id = query.message.message_id
        user_id = query.from_user.id
        
        parts = callback_data.split('_')
        if len(parts) < 4:
            return
        
        network = parts[2]
        contract = '_'.join(parts[3:])
        
        # Get or create session for consistent access pattern
        session = self.session_manager.get_session(chat_id, user_id)
        if not session:
            session = self.session_manager.create_session(chat_id, user_id, "Gem", contract, network, {})
        
        # Store in session for consistent access pattern
        session.current_contract = contract
        session.current_network = network
        
        # Get token data using session properties
        token_data = await self.api_client.get_token_info(session.current_network, session.current_contract)
        if not token_data:
            await query.edit_message_text("❌ Unable to fetch token data")
            return
        
        session.current_token = token_data.symbol
        session.current_token_data = token_data
        
        gem_handler = self.bot_handler.gem_research_handler
        gem_session = gem_handler.create_or_get_session(chat_id, user_id)
        
        if gem_session.criteria:
            message, buttons = gem_handler.format_balz_rank_message(token_data, gem_session.criteria)
        else:
            # Fallback if no criteria
            from ..bot.gem_research_handler import GemCriteria
            default_criteria = GemCriteria(network=network, age='early', liquidity='50_250', mcap='small')
            message, buttons = gem_handler.format_balz_rank_message(token_data, default_criteria)
        
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=buttons
        )
        # Schedule deletion
        deletion_time = 25 * 60  # 25 minutes
        await self._schedule_message_deletion(chat_id, message_id, deletion_time)
    
    async def _handle_gem_navigation(self, query, callback_data: str, direction: str):
        """Handle gem result navigation"""
        chat_id = query.message.chat_id
        user_id = query.from_user.id
        message_id = query.message.message_id
        
        gem_handler = self.bot_handler.gem_research_handler
        session = gem_handler.create_or_get_session(chat_id, user_id)
        
        if not session.results:
            await query.edit_message_text("Session expired. Please start a new search.")
            return
        
        # Update index
        if direction == 'next':
            session.current_index = min(session.current_index + 1, len(session.results) - 1)
        else:  # back
            session.current_index = max(session.current_index - 1, 0)
        
        # Show new gem
        current_gem = session.results[session.current_index]
        message, buttons = gem_handler.format_single_gem_result_from_pool(
            current_gem, session.criteria, session.current_index, len(session.results)
        )
        
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=buttons
        )
        # Schedule deletion
        deletion_time = 25 * 60  # 25 minutes
        await self._schedule_message_deletion(chat_id, message_id, deletion_time)
    
    async def _handle_back_to_gem(self, query, callback_data: str):
        """Handle back to gem from detail view"""
        chat_id = query.message.chat_id
        user_id = query.from_user.id
        message_id = query.message.message_id
        
        gem_handler = self.bot_handler.gem_research_handler
        session = gem_handler.create_or_get_session(chat_id, user_id)
        
        if not session.results or session.current_index >= len(session.results):
            await query.edit_message_text("Session expired. Please start a new search.")
            return
        
        # Show current gem
        current_gem = session.results[session.current_index]
        message, buttons = gem_handler.format_single_gem_result_from_pool(
            current_gem, session.criteria, session.current_index, len(session.results)
        )
        
        await query.edit_message_text(
            message,
            parse_mode='Markdown',
            reply_markup=buttons
        )
        # Schedule deletion
        deletion_time = 25 * 60  # 25 minutes
        await self._schedule_message_deletion(chat_id, message_id, deletion_time)
    
    def _format_balz_response(self, classification, token_symbol: str) -> str:
        """Format BALZ classification response"""
        header = f"⚖️ **BALZ RANK: {classification.category.value}**"
        
        return f"""{header}

**Token:** {token_symbol}
**Confidence:** {getattr(classification, 'confidence', 'N/A')}

**Analysis:** {getattr(classification, 'reasoning', 'Classification complete')}

{self._get_random_savage_line()}"""
    
    def _generate_fallback_balz_response(self, classification, token_data: Dict[str, Any]) -> str:
        """Generate fallback BALZ response without OpenAI"""
        symbol = token_data.get('symbol', 'UNKNOWN')
        
        header = f"BALZ RANK: {classification.emoji} {classification.category.value}"
        if classification.sub_category:
            header += f" | {classification.sub_category}"
        
        return f"""{header}

**Token:** {symbol}

**Tier Analysis:**
• Volume: {classification.volume_tier}
• Liquidity: {classification.liquidity_tier}
• Market Cap: {classification.market_cap_tier}
• FDV Ratio: {classification.fdv_ratio_tier}

**Assessment:** {classification.reasoning}

{self._get_random_savage_line()}"""
    
    async def handle_alert_analyze_button(self, query, callback_data: str):
        """Handle alert analyze button press"""
        try:
            chat_id = query.message.chat_id
            session = self.session_manager.get_session(chat_id, 0)  # Use 0 for broadcast user_id
            
            if not session or not hasattr(session, 'alert_context'):
                await query.edit_message_text("❌ Alert context expired. Please wait for new alerts.")
                return
            
            alert_context = session.alert_context
            contract = alert_context['contract']
            network = alert_context['network']
            
            # Store in session for consistent access pattern
            session.current_contract = contract
            session.current_network = network
            session.current_token = alert_context['symbol']
            
            # Get token info and analyze like normal token analysis
            await query.edit_message_text("🔍 Analyzing token from alert...")
            
            token_data = await self.api_client.get_token_info(session.current_network, session.current_contract)
            if not token_data:
                await query.edit_message_text("❌ Unable to fetch token data. Please try again.")
                return
            
            session.current_token_data = token_data
            
            # Format token overview
            from ..bot.message_formatter import MessageFormatter
            overview = MessageFormatter.format_token_overview(token_data)
            
            # Create main buttons
            buttons = self.create_token_overview_buttons()
            
            await query.edit_message_text(overview, reply_markup=buttons, parse_mode='Markdown')
            
            deletion_time = 25 * 60
            await self._schedule_message_deletion(chat_id, query.message.message_id, deletion_time)
            
        except Exception as e:
            logger.error(f"Error handling alert analyze button: {e}")
            await query.edit_message_text("❌ Error analyzing token. Please try again.")
    
    async def handle_alert_socials_button(self, query, callback_data: str):
        """Handle alert socials button press"""
        try:
            chat_id = query.message.chat_id
            session = self.session_manager.get_session(chat_id, 0)
            
            if not session or not hasattr(session, 'alert_context'):
                await query.edit_message_text("❌ Alert context expired. Please wait for new alerts.")
                return
            
            alert_context = session.alert_context
            contract = alert_context['contract']
            network = alert_context['network']
            symbol = alert_context['symbol']
            
            # Store in session for consistent access pattern
            session.current_contract = contract
            session.current_network = network
            session.current_token = symbol
            
            # Get social data using session properties
            social_data = await self.api_client.get_social_info(session.current_network, session.current_contract)
            
            if social_data:
                response = self._format_social_response(social_data, session.current_token)
            else:
                response = f"📱 **Social Links for {session.current_token}**\n\n" \
                          "ℹ️ No social information available for this token."
            
            # Create back button
            back_button = InlineKeyboardMarkup([
                [InlineKeyboardButton("← Back to Alert", callback_data="back_to_alert")]
            ])
            
            await query.edit_message_text(response, reply_markup=back_button, parse_mode='Markdown')
            
            deletion_time = 25 * 60
            await self._schedule_message_deletion(chat_id, query.message.message_id, deletion_time)
            
        except Exception as e:
            logger.error(f"Error handling alert socials button: {e}")
            await query.edit_message_text("❌ Error fetching social data. Please try again.")
    
    async def handle_alert_whale_button(self, query, callback_data: str):
        """Handle alert whale button press"""
        try:
            chat_id = query.message.chat_id
            session = self.session_manager.get_session(chat_id, 0)
            
            if not session or not hasattr(session, 'alert_context'):
                await query.edit_message_text("❌ Alert context expired. Please wait for new alerts.")
                return
            
            alert_context = session.alert_context
            contract = alert_context['contract']
            network = alert_context['network']
            symbol = alert_context['symbol']
            
            # Store in session for consistent access pattern
            session.current_contract = contract
            session.current_network = network
            session.current_token = symbol
            
            response = f"🐋 **Whale Tracker: {session.current_token}**\n\n" \
                      "❌ Unable to analyze whale activity for alerts.\n\n" \
                      "For full whale analysis, use the 📊 Token Details button first."
            
            # Create back button
            back_button = InlineKeyboardMarkup([
                [InlineKeyboardButton("← Back to Alert", callback_data="back_to_alert")]
            ])
            
            await query.edit_message_text(response, reply_markup=back_button, parse_mode='Markdown')
            
            deletion_time = 25 * 60
            await self._schedule_message_deletion(chat_id, query.message.message_id, deletion_time)
            
        except Exception as e:
            logger.error(f"Error handling alert whale button: {e}")
            await query.edit_message_text("❌ Error with whale tracker. Please try again.")
    
    async def handle_alert_balz_button(self, query, callback_data: str):
        """Handle alert BALZ button press"""
        try:
            chat_id = query.message.chat_id
            session = self.session_manager.get_session(chat_id, 0)
            
            if not session or not hasattr(session, 'alert_context'):
                await query.edit_message_text("❌ Alert context expired. Please wait for new alerts.")
                return
            
            alert_context = session.alert_context
            contract = alert_context['contract']
            network = alert_context['network']
            symbol = alert_context['symbol']
            
            # Store in session for consistent access pattern
            session.current_contract = contract
            session.current_network = network
            session.current_token = symbol
            
            # Get token data for BALZ analysis using session properties
            token_data = await self.api_client.get_token_info(session.current_network, session.current_contract)
            if not token_data:
                await query.edit_message_text("❌ Unable to fetch token data for BALZ analysis.")
                return
            
            session.current_token_data = token_data
            
            # Generate BALZ classification
            classification = self.reasoning_engine.classify_token(token_data)
            response = self._format_balz_response(classification, session.current_token)
            
            # Create back button
            back_button = InlineKeyboardMarkup([
                [InlineKeyboardButton("← Back to Alert", callback_data="back_to_alert")]
            ])
            
            await query.edit_message_text(response, reply_markup=back_button, parse_mode='Markdown')
            
            deletion_time = 25 * 60
            await self._schedule_message_deletion(chat_id, query.message.message_id, deletion_time)
            
        except Exception as e:
            logger.error(f"Error handling alert BALZ button: {e}")
            await query.edit_message_text("❌ Error generating BALZ analysis. Please try again.")
    
    async def handle_back_to_alert_button(self, query, callback_data: str):
        """Handle back to alert button press"""
        try:
            chat_id = query.message.chat_id
            
            # Parse contract and network from callback data
            parts = callback_data.split('_')
            if len(parts) >= 4:
                network = parts[2]
                contract = '_'.join(parts[3:])
                
                # Recreate buttons with proper contract/network info
                buttons = self.create_moonshot_buttons(contract, network)
                
                alert_message = f"📊 **Token Alert**\n\n📱 **Contract:** `{contract}`\n\n🌐 **Network:** {network.upper()}\n\n_Select an option below:_"
            else:
                # Fallback for malformed callback data
                alert_message = "📊 **Token Alert**\n\n_Select an option below:_"
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                buttons = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("📊 Token Details", callback_data="alert_analyze"),
                        InlineKeyboardButton("📱 Socials", callback_data="alert_socials")
                    ],
                    [
                        InlineKeyboardButton("🐋 Whale Tracker", callback_data="alert_whale"),
                        InlineKeyboardButton("⚖️ BALZ Rank", callback_data="alert_balz")
                    ]
                ])
            
            await query.edit_message_text(
                alert_message,
                reply_markup=buttons,
                parse_mode='Markdown'
            )
            
            deletion_time = 25 * 60
            await self._schedule_message_deletion(chat_id, query.message.message_id, deletion_time)
            
        except Exception as e:
            logger.error(f"Error handling back to alert button: {e}")
            await query.edit_message_text("❌ Error returning to alert. Please try again.")
