"""
Gem Research Handler for BIGBALZ Bot
Handles interactive gem research flow with 5-question journey
"""

import logging
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from ..api.geckoterminal_client import TokenData

logger = logging.getLogger(__name__)


@dataclass
class GemCriteria:
    """Gem research criteria from user selections"""
    network: str
    age: str  # 'fresh' or 'early'
    liquidity: str  # '10_50', '50_250', '250_1000', '1000_plus'
    mcap: str  # 'micro', 'small', 'mid'


@dataclass
class GemResearchSession:
    """User gem research session state"""
    chat_id: int
    user_id: int
    step: str  # 'network', 'age', 'liquidity', 'mcap', 'results'
    criteria: Optional[GemCriteria] = None
    results: List[TokenData] = None
    current_index: int = 0
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.results is None:
            self.results = []


@dataclass
class GemClassification:
    """Gem classification with risk assessment"""
    name: str
    emoji: str
    risk_level: str
    potential_returns: str
    fdv_note: str


class GemResearchHandler:
    """
    Handles gem research flow following existing bot patterns
    """
    
    def __init__(self, api_client, session_manager, bot_handler=None):
        """
        Initialize gem research handler
        
        Args:
            api_client: GeckoTerminal API client
            session_manager: Session state manager
            bot_handler: Reference to telegram bot handler
        """
        self.api_client = api_client
        self.session_manager = session_manager
        self.bot_handler = bot_handler
        
        # Gem research sessions (chat_id -> GemResearchSession)
        self.research_sessions = {}
        self.session_ttl = 600  # 10 minutes
        
        # Classification mappings
        self.classifications = {
            'degen_play': GemClassification(
                name="POTENTIAL DEGEN PLAY",
                emoji="🚀",
                risk_level="Extreme",
                potential_returns="100x possible",
                fdv_note="Often high FDV/MCap ratio (red flag)"
            ),
            'early_gem': GemClassification(
                name="POTENTIAL EARLY GEM", 
                emoji="💎",
                risk_level="Very High",
                potential_returns="10-50x possible",
                fdv_note="Look for reasonable FDV/MCap ratio"
            ),
            'growing_project': GemClassification(
                name="POTENTIAL GROWING PROJECT",
                emoji="🌱", 
                risk_level="High",
                potential_returns="5-20x realistic",
                fdv_note="Check FDV for true valuation"
            ),
            'momentum_play': GemClassification(
                name="POTENTIAL MOMENTUM PLAY",
                emoji="⚡",
                risk_level="Medium-High", 
                potential_returns="3-10x short term",
                fdv_note="High liquidity might be explained by FDV"
            ),
            'established_mover': GemClassification(
                name="POTENTIAL ESTABLISHED MOVER",
                emoji="🏛️",
                risk_level="Medium",
                potential_returns="2-5x steady", 
                fdv_note="Usually better FDV/MCap ratios"
            ),
            'safe_bet': GemClassification(
                name="POTENTIAL SAFE BET",
                emoji="🛡️",
                risk_level="Lower (crypto standards)",
                potential_returns="2-3x stable",
                fdv_note="Should have most tokens circulating"
            ),
            'liquidity_trap': GemClassification(
                name="POTENTIAL LIQUIDITY TRAP",
                emoji="🎰",
                risk_level="Extreme",
                potential_returns="Could be next big thing or scam",
                fdv_note="Check if FDV manipulation explains high liquidity"
            ),
            'zombie_coin': GemClassification(
                name="POTENTIAL ZOMBIE COIN",
                emoji="💀",
                risk_level="Extreme", 
                potential_returns="Possible revival",
                fdv_note="Usually terrible metrics all around"
            )
        }
        
        logger.info("Gem research handler initialized")
    
    def create_choice_buttons(self) -> InlineKeyboardMarkup:
        """Create initial choice buttons for moonshots vs gem research"""
        keyboard = [
            [
                InlineKeyboardButton("🚀 Recent Moonshots", callback_data="choice_moonshots"),
                InlineKeyboardButton("🔍 Research Gems", callback_data="choice_gems")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def create_network_selection_buttons(self) -> InlineKeyboardMarkup:
        """Create network selection buttons"""
        keyboard = [
            [
                InlineKeyboardButton("⚡ Solana", callback_data="gem_network_solana"),
                InlineKeyboardButton("🔷 Ethereum", callback_data="gem_network_eth")
            ],
            [
                InlineKeyboardButton("🟡 BSC", callback_data="gem_network_bsc"),
                InlineKeyboardButton("🔵 Base", callback_data="gem_network_base")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def create_age_selection_buttons(self) -> InlineKeyboardMarkup:
        """Create age selection buttons"""
        keyboard = [
            [
                InlineKeyboardButton("🆕 Fresh Launches", callback_data="gem_age_fresh"),
                InlineKeyboardButton("📅 Early Stage", callback_data="gem_age_early")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def create_liquidity_selection_buttons(self) -> InlineKeyboardMarkup:
        """Create liquidity range selection buttons"""
        keyboard = [
            [
                InlineKeyboardButton("$10K-$50K", callback_data="gem_liq_10_50"),
                InlineKeyboardButton("$50K-$250K", callback_data="gem_liq_50_250")
            ],
            [
                InlineKeyboardButton("$250K-$1M", callback_data="gem_liq_250_1000"),
                InlineKeyboardButton("$1M+", callback_data="gem_liq_1000_plus")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def create_mcap_selection_buttons(self) -> InlineKeyboardMarkup:
        """Create market cap range selection buttons"""
        keyboard = [
            [
                InlineKeyboardButton("💎 Micro", callback_data="gem_mcap_micro"),
                InlineKeyboardButton("💰 Small", callback_data="gem_mcap_small"),
                InlineKeyboardButton("🏆 Mid", callback_data="gem_mcap_mid")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def create_gem_action_buttons(self, network: str, contract: str, 
                                 current_index: int, total_gems: int) -> InlineKeyboardMarkup:
        """Create action buttons for individual gem results"""
        buttons = [
            [
                InlineKeyboardButton("📊 Token Details", callback_data=f"gem_analyze_{network}_{contract}"),
                InlineKeyboardButton("📱 Socials", callback_data=f"gem_socials_{network}_{contract}")
            ],
            [
                InlineKeyboardButton("🐋 Whale Tracker", callback_data=f"gem_whale_{network}_{contract}"),
                InlineKeyboardButton("⚖️ BALZ Rank", callback_data=f"gem_balz_{network}_{contract}")
            ]
        ]
        
        # Navigation buttons
        nav_buttons = []
        
        # Back button (if not first gem)
        if current_index > 0:
            nav_buttons.append(InlineKeyboardButton("← Back", callback_data=f"gem_back_{current_index}"))
        
        # Next button (if not last gem)
        if current_index < total_gems - 1:
            remaining = total_gems - current_index - 1
            nav_buttons.append(InlineKeyboardButton(f"Next → ({remaining} more)", callback_data=f"gem_next_{current_index}"))
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        # Always add new search button
        buttons.append([InlineKeyboardButton("🔄 New Search", callback_data="choice_gems")])
        
        return InlineKeyboardMarkup(buttons)
    
    def create_no_gems_buttons(self) -> InlineKeyboardMarkup:
        """Create buttons for no gems found scenario"""
        keyboard = [
            [
                InlineKeyboardButton("🔄 Adjust Search", callback_data="choice_gems"),
                InlineKeyboardButton("🚀 Show Moonshots", callback_data="choice_moonshots")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def create_gem_detail_back_button(self, current_index: int) -> InlineKeyboardMarkup:
        """Create back button for gem detail views"""
        keyboard = [
            [InlineKeyboardButton("← Back to Gem", callback_data=f"back_to_gem_{current_index}")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def get_choice_message(self) -> Tuple[str, InlineKeyboardMarkup]:
        """Get the initial choice message and buttons"""
        message = """Yo, I can do two things for you:

Show you high-risk moonshots I may have detected in the last 45 minutes from my monitoring, or do custom research to find gems based on your specific criteria.

What you feeling?"""
        
        return message, self.create_choice_buttons()
    
    def get_network_selection_message(self) -> Tuple[str, InlineKeyboardMarkup]:
        """Get network selection message and buttons"""
        message = """Alright, let's hunt for gems. 

First up - which network you tryna explore?"""
        
        return message, self.create_network_selection_buttons()
    
    def get_age_selection_message(self) -> Tuple[str, InlineKeyboardMarkup]:
        """Get age selection message and buttons"""
        message = """How old should your potential gems be?

🆕 Fresh Launches = Last 48 hours
📅 Early Stage = 3-7 days old

Note: Tokens older than 7 days are usually already discovered"""
        
        return message, self.create_age_selection_buttons()
    
    def get_liquidity_selection_message(self) -> Tuple[str, InlineKeyboardMarkup]:
        """Get liquidity selection message and buttons"""
        message = """Minimum liquidity pool?

Higher liquidity = easier to exit but might miss early gains
Lower liquidity = earlier entry but harder to sell"""
        
        return message, self.create_liquidity_selection_buttons()
    
    def get_mcap_selection_message(self) -> Tuple[str, InlineKeyboardMarkup]:
        """Get market cap selection message and buttons"""
        message = """What's your target market cap range?

This affects potential returns - smaller caps can pump harder but carry way more risk.

💎 Micro = Under $1M (lottery tickets)
💰 Small = $1M-$10M (high growth potential)
🏆 Mid = $10M-$50M (more established)"""
        
        return message, self.create_mcap_selection_buttons()
    
    def get_research_loading_message(self, criteria: GemCriteria) -> str:
        """Get research loading message"""
        network_names = {
            'solana': 'Solana',
            'eth': 'Ethereum', 
            'bsc': 'BSC',
            'base': 'Base'
        }
        
        age_ranges = {
            'fresh': 'Last 48 hours',
            'early': '3-7 days old'
        }
        
        liq_ranges = {
            '10_50': '$10K-$50K',
            '50_250': '$50K-$250K',
            '250_1000': '$250K-$1M', 
            '1000_plus': '$1M+'
        }
        
        mcap_ranges = {
            'micro': 'Under $1M',
            'small': '$1M-$10M',
            'mid': '$10M-$50M'
        }
        
        return f"""🔍 Researching {network_names.get(criteria.network, criteria.network)} gems...

Looking for:
• Age: {age_ranges.get(criteria.age, criteria.age)}
• Liquidity: {liq_ranges.get(criteria.liquidity, criteria.liquidity)}
• Market Cap: {mcap_ranges.get(criteria.mcap, criteria.mcap)}

Scanning pools... ⏳"""
    
    def get_no_gems_message(self, network: str) -> Tuple[str, InlineKeyboardMarkup]:
        """Get no gems found message and buttons"""
        network_names = {
            'solana': 'Solana',
            'eth': 'Ethereum',
            'bsc': 'BSC', 
            'base': 'Base'
        }
        
        message = f"""Searched through hundreds of pools on {network_names.get(network, network)}...

No gems matching your exact criteria right now.

Market conditions:
- Your filters might be too specific
- Try wider ranges for better results
- Or check what I caught in my moonshot nets"""
        
        return message, self.create_no_gems_buttons()
    
    def create_or_get_session(self, chat_id: int, user_id: int) -> GemResearchSession:
        """Create or get existing gem research session"""
        session_key = f"{chat_id}_{user_id}"
        
        # Clean up expired sessions
        current_time = time.time()
        expired_keys = []
        for key, session in self.research_sessions.items():
            if current_time - session.timestamp > self.session_ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.research_sessions[key]
        
        # Create new session or return existing
        if session_key not in self.research_sessions:
            self.research_sessions[session_key] = GemResearchSession(
                chat_id=chat_id,
                user_id=user_id,
                step='network'
            )
        
        return self.research_sessions[session_key]
    
    def update_session_step(self, chat_id: int, user_id: int, step: str, **kwargs):
        """Update session step and criteria"""
        session = self.create_or_get_session(chat_id, user_id)
        session.step = step
        session.timestamp = time.time()
        
        # Initialize criteria if needed
        if session.criteria is None:
            session.criteria = GemCriteria(
                network='', age='', liquidity='', mcap=''
            )
        
        # Update criteria fields
        for key, value in kwargs.items():
            if hasattr(session.criteria, key):
                setattr(session.criteria, key, value)
    
    def classify_gem(self, token_data: TokenData, criteria: GemCriteria) -> GemClassification:
        """Classify gem based on criteria and metrics"""
        mcap = token_data.market_cap_usd
        liquidity = token_data.liquidity_usd
        age = criteria.age
        
        # Convert liquidity criteria to actual ranges
        liq_ranges = {
            '10_50': (10000, 50000),
            '50_250': (50000, 250000),
            '250_1000': (250000, 1000000),
            '1000_plus': (1000000, float('inf'))
        }
        
        liq_min, liq_max = liq_ranges.get(criteria.liquidity, (0, float('inf')))
        
        # Classification logic from spec
        
        # 1. POTENTIAL DEGEN PLAY
        if (criteria.mcap == 'micro' and mcap < 1000000 and 
            criteria.liquidity == '10_50' and age == 'fresh'):
            return self.classifications['degen_play']
        
        # 2. POTENTIAL EARLY GEM  
        if (criteria.mcap == 'micro' and mcap < 1000000 and
            criteria.liquidity == '50_250' and age == 'early'):
            return self.classifications['early_gem']
        
        # 3. POTENTIAL GROWING PROJECT
        if (criteria.mcap == 'small' and 1000000 <= mcap <= 10000000 and
            criteria.liquidity in ['50_250', '250_1000'] and age == 'early'):
            return self.classifications['growing_project']
        
        # 4. POTENTIAL MOMENTUM PLAY
        if (criteria.mcap == 'small' and 1000000 <= mcap <= 10000000 and
            criteria.liquidity in ['250_1000', '1000_plus'] and age == 'early'):
            return self.classifications['momentum_play']
        
        # 5. POTENTIAL ESTABLISHED MOVER
        if (criteria.mcap == 'mid' and 10000000 <= mcap <= 50000000 and
            liquidity >= 500000 and age == 'early'):
            return self.classifications['established_mover']
        
        # 6. POTENTIAL SAFE BET
        if (criteria.mcap == 'mid' and 10000000 <= mcap <= 50000000 and
            criteria.liquidity == '1000_plus' and age == 'early'):
            return self.classifications['safe_bet']
        
        # 7. POTENTIAL LIQUIDITY TRAP
        if (criteria.mcap == 'micro' and mcap < 1000000 and
            liquidity >= 250000 and age == 'fresh'):
            return self.classifications['liquidity_trap']
        
        # 8. POTENTIAL ZOMBIE COIN (fallback for low liquidity)
        if liquidity < 50000:
            return self.classifications['zombie_coin']
        
        # Default to early gem if no specific match
        return self.classifications['early_gem']
    
    def format_fdv_analysis(self, token_data: TokenData) -> str:
        """Format FDV/MCap ratio analysis"""
        if token_data.market_cap_usd > 0 and token_data.fdv_usd > 0:
            ratio = token_data.fdv_usd / token_data.market_cap_usd
            circulating_percent = (token_data.market_cap_usd / token_data.fdv_usd) * 100
            
            if ratio > 10:
                return f"⚠️ High dilution risk - only {circulating_percent:.0f}% tokens circulating"
            elif ratio >= 2:
                return f"Moderate dilution - {circulating_percent:.0f}% tokens circulating"
            else:
                return f"✅ Low dilution risk - {circulating_percent:.0f}% tokens circulating"
        
        return "FDV data not available"
    
    def format_single_gem_result(self, token_data: TokenData, criteria: GemCriteria,
                                current_index: int, total_gems: int) -> Tuple[str, InlineKeyboardMarkup]:
        """Format single gem result message"""
        classification = self.classify_gem(token_data, criteria)
        fdv_analysis = self.format_fdv_analysis(token_data)
        
        # Format numbers
        from ..bot.message_formatter import MessageFormatter
        price = MessageFormatter._format_price(token_data.price_usd)
        market_cap = MessageFormatter._format_large_number(token_data.market_cap_usd)
        fdv = MessageFormatter._format_large_number(token_data.fdv_usd)
        liquidity = MessageFormatter._format_large_number(token_data.liquidity_usd)
        volume = MessageFormatter._format_large_number(token_data.volume_24h)
        
        # Calculate circulating percentage
        circulating_percent = 0
        if token_data.market_cap_usd > 0 and token_data.fdv_usd > 0:
            circulating_percent = (token_data.market_cap_usd / token_data.fdv_usd) * 100
        
        # Get network display name
        network_names = {
            'solana': 'Solana',
            'eth': 'Ethereum',
            'bsc': 'BSC',
            'base': 'Base'
        }
        network_display = network_names.get(token_data.network, token_data.network.upper())
        
        # Get timeframe for price change
        timeframe = "1h" if token_data.price_change_1h != 0 else "24h"
        price_change = token_data.price_change_1h if token_data.price_change_1h != 0 else token_data.price_change_24h
        
        # Estimate transaction count (approximation since we don't have exact data)
        tx_count = max(100, int(token_data.volume_24h / 1000)) if token_data.volume_24h > 0 else 0
        
        message = f"""Found 1 gem on {network_display} matching your criteria:

{classification.emoji} {classification.name}

${token_data.symbol}

💰 MCap: {market_cap} | FDV: {fdv} ({circulating_percent:.0f}% circulating)
💧 Liquidity: {liquidity}
📊 Volume 24h: {volume} | Txs: {tx_count}
📈 24h: {token_data.price_change_24h:+.1f}% | {timeframe}: {price_change:+.1f}%

📱 Contract: `{token_data.contract_address}`
🌐 Network: {network_display}

Real talk, this is gambling not investing 🎲

---

🔍 GEM CLASSIFICATIONS:

🚀 POTENTIAL DEGEN PLAY = Ultra early, 100x or zero
💎 POTENTIAL EARLY GEM = 10-50x possible, high risk
🌱 POTENTIAL GROWING PROJECT = 5-20x realistic
⚡ POTENTIAL MOMENTUM PLAY = 3-10x short term
🏛️ POTENTIAL ESTABLISHED MOVER = 2-5x steady
🛡️ POTENTIAL SAFE BET = 2-3x stable (in crypto terms)

---

⚠️ REALITY CHECK

FDV/MCap: {fdv_analysis}
Can't verify: Contract safety, holder distribution, team
High risk: Liquidity can vanish, prices can nuke
DYOR: This ain't financial advice"""

        buttons = self.create_gem_action_buttons(
            token_data.network, 
            token_data.contract_address,
            current_index, 
            total_gems
        )
        
        return message, buttons
    
    async def execute_gem_research(self, criteria: GemCriteria) -> List[TokenData]:
        """
        Execute gem research based on criteria
        
        Args:
            criteria: Research criteria from user
            
        Returns:
            List of TokenData objects matching criteria
        """
        try:
            logger.info(f"Executing gem research: {criteria.network}, {criteria.age}, {criteria.liquidity}, {criteria.mcap}")
            
            gems = []
            
            if criteria.age == 'fresh':
                # Fresh launches: Get new pools and filter
                gems = await self._search_fresh_launches(criteria)
            else:  # early
                # Early stage: Get pools and verify age with OHLCV
                gems = await self._search_early_stage(criteria)
            
            # Apply market cap filtering
            filtered_gems = self._filter_by_market_cap(gems, criteria.mcap)
            
            # Limit to 10 results max
            return filtered_gems[:10]
            
        except Exception as e:
            logger.error(f"Error executing gem research: {e}")
            return []
    
    async def _search_fresh_launches(self, criteria: GemCriteria) -> List[TokenData]:
        """Search for fresh launches (<48h old)"""
        try:
            # Get new pools
            pools = await self.api_client.get_new_pools(criteria.network, limit=50)
            if not pools:
                return []
            
            gems = []
            checked_count = 0
            
            for pool in pools:
                # Rate limiting - check max 15 tokens to stay under 30 calls/min
                if checked_count >= 15:
                    break
                
                # Extract liquidity from pool
                attrs = pool.get('attributes', {})
                liquidity = float(attrs.get('reserve_in_usd', 0))
                
                # Filter by liquidity first (cheaper than API calls)
                if not self._meets_liquidity_criteria(liquidity, criteria.liquidity):
                    continue
                
                # Extract contract address
                contract = self._extract_contract_from_pool(pool)
                if not contract:
                    continue
                
                # Get full token info
                token_data = await self.api_client.get_token_info(criteria.network, contract)
                if token_data:
                    gems.append(token_data)
                    checked_count += 1
            
            logger.info(f"Found {len(gems)} fresh launch gems after checking {checked_count} tokens")
            return gems
            
        except Exception as e:
            logger.error(f"Error searching fresh launches: {e}")
            return []
    
    async def _search_early_stage(self, criteria: GemCriteria) -> List[TokenData]:
        """Search for early stage gems (3-7 days old)"""
        try:
            # Get pools sorted by volume
            pools = await self.api_client.get_pools_search(
                criteria.network, 
                sort="h24_volume_usd_desc", 
                limit=100
            )
            if not pools:
                return []
            
            gems = []
            checked_count = 0
            
            for pool in pools:
                # Rate limiting - check max 10 tokens for early stage due to OHLCV calls
                if checked_count >= 10:
                    break
                
                # Extract liquidity from pool
                attrs = pool.get('attributes', {})
                liquidity = float(attrs.get('reserve_in_usd', 0))
                
                # Filter by liquidity first
                if not self._meets_liquidity_criteria(liquidity, criteria.liquidity):
                    continue
                
                # Verify age using OHLCV data
                pool_address = pool.get('id')  # Pool ID is the address
                if not pool_address:
                    continue
                
                # Get OHLCV data to verify age
                ohlcv_data = await self.api_client.get_pool_ohlcv(
                    criteria.network, 
                    pool_address,
                    timeframe="day",
                    aggregate=1,
                    limit=7
                )
                
                # Count candles to determine age
                if not ohlcv_data or len(ohlcv_data) < 3 or len(ohlcv_data) > 7:
                    continue  # Skip if not 3-7 days old
                
                # Extract contract and get token info
                contract = self._extract_contract_from_pool(pool)
                if not contract:
                    continue
                
                token_data = await self.api_client.get_token_info(criteria.network, contract)
                if token_data:
                    gems.append(token_data)
                    checked_count += 1
            
            logger.info(f"Found {len(gems)} early stage gems after checking {checked_count} tokens")
            return gems
            
        except Exception as e:
            logger.error(f"Error searching early stage gems: {e}")
            return []
    
    def _extract_contract_from_pool(self, pool: Dict) -> Optional[str]:
        """Extract contract address from pool relationships"""
        try:
            relationships = pool.get('relationships', {})
            base_token = relationships.get('base_token', {})
            base_token_data = base_token.get('data', {})
            base_token_id = base_token_data.get('id', '')
            
            if base_token_id and '_' in base_token_id:
                # Format is "network_contractaddress"
                return base_token_id.split('_', 1)[1]
            
            return None
        except Exception:
            return None
    
    def _meets_liquidity_criteria(self, liquidity: float, criteria: str) -> bool:
        """Check if liquidity meets criteria"""
        ranges = {
            '10_50': (10000, 50000),
            '50_250': (50000, 250000),
            '250_1000': (250000, 1000000),
            '1000_plus': (1000000, float('inf'))
        }
        
        min_liq, max_liq = ranges.get(criteria, (0, float('inf')))
        return min_liq <= liquidity <= max_liq
    
    def _filter_by_market_cap(self, gems: List[TokenData], mcap_criteria: str) -> List[TokenData]:
        """Filter gems by market cap criteria"""
        ranges = {
            'micro': (0, 1000000),
            'small': (1000000, 10000000),
            'mid': (10000000, 50000000)
        }
        
        min_mcap, max_mcap = ranges.get(mcap_criteria, (0, float('inf')))
        
        filtered = []
        for gem in gems:
            if min_mcap <= gem.market_cap_usd <= max_mcap:
                filtered.append(gem)
        
        return filtered
    
    def format_whale_tracker_message(self, token_symbol: str) -> Tuple[str, InlineKeyboardMarkup]:
        """Format whale tracker limitation message"""
        message = """🐋 Whale Analysis

Cannot analyze whale distribution through GeckoTerminal.

To check whales:
1. Go to blockchain explorer
2. Check "Holders" tab
3. Look for concentration in top wallets

Red flags:
- Top 10 wallets >50%
- Single wallet >10%
- Recent large accumulation"""
        
        # This would need the current index passed in, but for now we'll use 0
        buttons = self.create_gem_detail_back_button(0)
        return message, buttons
    
    def format_balz_rank_message(self, token_data: TokenData, criteria: GemCriteria) -> Tuple[str, InlineKeyboardMarkup]:
        """Format BALZ rank message for gems"""
        classification = self.classify_gem(token_data, criteria)
        
        # Calculate risk score based on available data
        risk_score = self._calculate_risk_score(token_data)
        
        # Determine BALZ category
        if risk_score >= 8:
            balz_category = "LARGE BALZ (Lower risk - crypto standards)"
        elif risk_score >= 6:
            balz_category = "MEDIUM BALZ (Moderate risk)"
        elif risk_score >= 4:
            balz_category = "SMALL BALZ (High risk)"
        else:
            balz_category = "MICRO BALZ (Extreme risk)"
        
        message = f"""⚖️ BALZ Rank Classification

{classification.emoji} {classification.name}

Risk Level: {classification.risk_level}
Potential Returns: {classification.potential_returns}

BALZ Category: {balz_category}

Risk Factors:
• Liquidity/MCap ratio
• Volume patterns
• Price volatility
• Age factor
• FDV/MCap ratio

{classification.fdv_note}"""
        
        buttons = self.create_gem_detail_back_button(0)
        return message, buttons
    
    def _calculate_risk_score(self, token_data: TokenData) -> float:
        """Calculate risk score from 0-10 (10 = lowest risk)"""
        score = 0
        
        # Liquidity factor (0-3 points)
        if token_data.liquidity_usd >= 1000000:
            score += 3
        elif token_data.liquidity_usd >= 300000:
            score += 2
        elif token_data.liquidity_usd >= 100000:
            score += 1
        
        # Volume factor (0-2 points)
        if token_data.volume_24h >= 100000:
            score += 2
        elif token_data.volume_24h >= 10000:
            score += 1
        
        # Market cap factor (0-2 points)
        if token_data.market_cap_usd >= 10000000:
            score += 2
        elif token_data.market_cap_usd >= 1000000:
            score += 1
        
        # FDV/MCap ratio factor (0-2 points)
        if token_data.fdv_usd > 0 and token_data.market_cap_usd > 0:
            ratio = token_data.fdv_usd / token_data.market_cap_usd
            if ratio < 2:
                score += 2
            elif ratio < 5:
                score += 1
        
        # Price stability factor (0-1 point)
        if abs(token_data.price_change_24h) < 20:
            score += 1
        
        return min(score, 10)
    
    def clear_session(self, chat_id: int, user_id: int):
        """Clear gem research session"""
        session_key = f"{chat_id}_{user_id}"
        if session_key in self.research_sessions:
            del self.research_sessions[session_key]