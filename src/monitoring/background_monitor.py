"""
Background Monitor for BIGBALZ Bot
Handles moonshot detection, rug monitoring, and status reports
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict
import time
import random

from src.api.geckoterminal_client import GeckoTerminalClient
from src.bot.telegram_handler import TelegramBotHandler
from src.algorithms.moonshot_criteria import MOONSHOT_CRITERIA_LIST, TIER_CONFIG
from src.algorithms.rug_detection import (
    RUG_LIQUIDITY_DRAIN_CRITERIA, 
    RUG_PRICE_CRASH_CRITERIA, 
    RUG_VOLUME_DUMP_CRITERIA,
    MAX_HISTORICAL_DATA_AGE
)


logger = logging.getLogger(__name__)


@dataclass
class RugAlert:
    """Data structure for rug pull alerts"""
    token_symbol: str
    contract: str
    network: str
    liquidity_drain_percent: float
    price_drop_percent: float
    volume_spike_percent: float
    final_liquidity: float
    final_volume_1h: float
    timestamp: datetime
    rug_type: str  # "LIQUIDITY_DRAIN", "PRICE_CRASH", "VOLUME_DUMP"


@dataclass
class MoonshotAlert:
    """Data structure for moonshot alerts"""
    token_symbol: str
    contract: str
    network: str
    tier: str  # "POTENTIAL 100X", "POTENTIAL 10X", "POTENTIAL 2X"
    price_change_percent: float
    volume_24h: float
    liquidity: float
    transaction_count: int
    timestamp: datetime
    price_usd: float  # Current token price


class BackgroundMonitor:
    """
    Monitors crypto markets for moonshots and rug pulls
    Runs background tasks and sends alerts
    """
    
    def __init__(self, api_client, bot_handler, settings):
        """
        Initialize background monitor
        
        Args:
            api_client: GeckoTerminal API client
            bot_handler: Telegram bot handler for broadcasts
            settings: Monitoring configuration
        """
        self.api_client = api_client
        self.bot_handler = bot_handler
        self.settings = settings
        self.running = False
        self.tasks = []
        
        # Track detected moonshots to avoid duplicates
        self.detected_moonshots = {}  # contract -> MoonshotAlert object
        self.moonshot_cooldown = 3600  # 1 hour cooldown
        
        # Track pools for both moonshot and rug detection
        self.tracked_pools = {}
        self.pool_history = defaultdict(list)  # pool_id -> list of historical data (used for BOTH moonshots and rugs)
        self.detected_rugs = {}  # contract -> RugAlert object
        self.rug_cooldown = 3600  # 1 hour cooldown
        
        # Statistics
        self.stats = {
            'moonshots_detected': 0,
            'rugs_detected': 0,
            'last_status_report': datetime.utcnow()
        }
        
        logger.info("Background monitor initialized")
    
    async def start(self):
        """Start all background monitoring tasks"""
        if self.running:
            logger.warning("Background monitor already running")
            return
        
        self.running = True
        logger.info("=" * 60)
        logger.info("🚀 STARTING BACKGROUND MONITORING SYSTEM")
        logger.info(f"Moonshot scan interval: {self.settings.moonshot_scan_interval}s")
        logger.info(f"Rug scan interval: {self.settings.rug_scan_interval}s")
        logger.info(f"Status report interval: {self.settings.status_report_interval}s ({self.settings.status_report_interval/60:.0f} minutes)")
        logger.info("=" * 60)
        
        # Create monitoring tasks
        self.tasks = [
            asyncio.create_task(self._moonshot_monitor()),
            asyncio.create_task(self._rug_monitor()),
            asyncio.create_task(self._status_reporter()),
            asyncio.create_task(self._vibe_checker())
        ]
        
        logger.info(f"✅ Created {len(self.tasks)} background tasks")
        
        # Wait for all tasks
        try:
            await asyncio.gather(*self.tasks)
        except asyncio.CancelledError:
            logger.info("Background monitoring cancelled")
    
    async def stop(self):
        """Stop all background monitoring tasks"""
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for cancellation
        await asyncio.gather(*self.tasks, return_exceptions=True)
        
        logger.info("Background monitoring stopped")
    
    async def _moonshot_monitor(self):
        """Monitor for moonshot opportunities"""
        logger.info("🚀 Moonshot monitor started")
        logger.info(f"Scanning interval: {self.settings.moonshot_scan_interval}s")
        
        scan_count = 0
        while self.running:
            try:
                scan_count += 1
                logger.info(f"🔍 Starting moonshot scan #{scan_count}")
                
                # Scan different networks for moonshots
                networks = ['eth', 'solana', 'bsc', 'base']
                
                for network in networks:
                    logger.debug(f"Scanning {network} network for moonshots...")
                    # Check trending pools
                    await self._scan_network_for_moonshots(network, 'trending')
                    # Check new pools
                    await self._scan_network_for_moonshots(network, 'new')
                
                logger.info(f"✅ Moonshot scan #{scan_count} complete, waiting {self.settings.moonshot_scan_interval}s")
                await asyncio.sleep(self.settings.moonshot_scan_interval)
                
            except Exception as e:
                logger.error(f"Error in moonshot monitor: {e}")
                await asyncio.sleep(60)  # Wait before retry
    
    async def _rug_monitor(self):
        """Monitor for rug pulls"""
        logger.info("☠️ Rug monitor started")
        logger.info(f"Scanning interval: {self.settings.rug_scan_interval}s")
        
        scan_count = 0
        while self.running:
            try:
                scan_count += 1
                logger.info(f"🔍 Starting rug scan #{scan_count}")
                
                # Scan different networks for rugs
                networks = ['eth', 'solana', 'bsc', 'base']
                
                for network in networks:
                    logger.debug(f"Scanning {network} network for rugs...")
                    await self._scan_network_for_rugs(network)
                
                # Clean up old history
                self._cleanup_old_history()
                
                logger.info(f"✅ Rug scan #{scan_count} complete, waiting {self.settings.rug_scan_interval}s")
                await asyncio.sleep(self.settings.rug_scan_interval)
                
            except Exception as e:
                logger.error(f"Error in rug monitor: {e}")
                await asyncio.sleep(60)  # Wait before retry
    
    async def _status_reporter(self):
        """Send periodic status reports"""
        logger.info("📊 Status reporter started")
        logger.info(f"Report interval: {self.settings.status_report_interval}s ({self.settings.status_report_interval/60:.1f} minutes)")
        
        report_count = 0
        while self.running:
            try:
                # Wait for the interval first
                await asyncio.sleep(self.settings.status_report_interval)
                
                report_count += 1
                logger.info(f"📊 Generating status report #{report_count}")
                
                # Generate and send status report
                report, buttons = self._generate_status_report()
                await self.bot_handler.broadcast_alert(report, buttons)
                
                # Update last report time
                self.stats['last_status_report'] = datetime.utcnow()
                
                logger.info(f"✅ Status report #{report_count} sent - Moonshots: {self.stats['moonshots_detected']}, "
                          f"Rugs: {self.stats['rugs_detected']}")
                
            except Exception as e:
                logger.error(f"Error in status reporter: {e}")
                await asyncio.sleep(300)  # Wait 5 min before retry
    
    async def _vibe_checker(self):
        """Send periodic positive vibes when chat is quiet"""
        logger.info("🌙 Vibe checker started")
        logger.info("Will drop positive vibes every 90 minutes if chat is quiet")
        
        while self.running:
            try:
                # Wait 90 minutes
                await asyncio.sleep(5400)  # 90 minutes
                
                logger.info("🌙 Dropping positive vibes")
                
                # Positive vibe messages
                vibe_messages = [
                    "yo btw this cycle is gonna be different\n\nwe're all gonna make it fr",
                    "just thinking about how we're all gonna be rich soon\n\ngenerational wealth incoming",
                    "remember when we thought 10x was good?\n\nthis cycle we going 100x minimum",
                    "can't wait to see y'all pulling up in lambos\n\nit's not if, it's when",
                    "bear market made us strong\n\nbull market gonna make us rich",
                    "imagine looking back at these prices next year\n\nwe're so early it's not even funny",
                    "fuck you money loading...\n\nestimated time: this cycle",
                    "who else ready for life changing gains?\n\nbecause they're coming",
                    "private jets and yachts aren't dreams\n\nthey're just pending transactions",
                    "remember this moment when you're rich\n\nwe called it",
                    "the matrix can't hold us back anymore\n\nfinancial freedom imminent",
                    "diamond hands get diamond rewards\n\nand we're about to prove it",
                    "patience separates winners from losers\n\nand we're all winners here",
                    "your future self is gonna thank you\n\nfor not giving up now",
                    "wagmi isn't just a meme\n\nit's a prophecy",
                    "every dip is just a discount\n\nfor future millionaires",
                    "compound gains hit different\n\nwhen you believe in the vision",
                    "retirement before 30?\n\nthat's the baseline now",
                    "they called us degens\n\nwe'll call them poor",
                    "this is the wealth transfer they warned about\n\nand we're on the right side",
                    "moon mission status: boarding\n\nfirst class only",
                    "your bank account about to look like a phone number\n\ninternational dialing code included",
                    "generational poverty ends with us\n\ngenerational wealth starts now",
                    "scared money don't make money\n\nand we ain't scared of shit",
                    "the best time to buy was yesterday\n\nsecond best time is now",
                    "bulls make money, bears make money\n\ndiamonds hands make fortunes",
                    "we're not lucky\n\nwe're just early and not wrong",
                    "imagine not being bullish right now\n\ncouldn't be us",
                    "financial advisors hate this one simple trick:\n\nactually making money",
                    "the real flippening?\n\nwhen our portfolios flip our parents' net worth"
                ]
                
                message = random.choice(vibe_messages)
                await self.bot_handler.broadcast_alert(message)
                
                logger.info("✅ Positive vibes sent")
                
            except Exception as e:
                logger.error(f"Error in vibe checker: {e}")
                await asyncio.sleep(1800)  # Wait 30 min before retry
    
    async def _scan_network_for_rugs(self, network: str):
        """Scan a specific network for rug pulls"""
        try:
            # Get trending pools from multiple timeframes
            all_pools = []
            timeframes = ['5m', '1h', '6h', '24h']
            
            for timeframe in timeframes:
                logger.debug(f"Checking {network} trending pools for rugs - {timeframe}")
                pools = await self.api_client.get_trending_pools(network, duration=timeframe, limit=20)
                if pools:
                    all_pools.extend(pools)
            
            if not all_pools:
                logger.warning(f"No pools returned for {network} rug monitoring")
                return
            
            # Deduplicate pools by pool_id
            seen_pools = {}
            unique_pools = []
            for pool in all_pools:
                pool_id = pool.get('id')
                if pool_id and pool_id not in seen_pools:
                    seen_pools[pool_id] = True
                    unique_pools.append(pool)
            
            logger.info(f"Checking {len(unique_pools)} unique pools on {network} for rugs")
            
            # Log first pool structure for debugging
            if unique_pools and not hasattr(self, '_logged_rug_pool'):
                logger.info(f"Rug pool structure: {unique_pools[0].get('attributes', {}).keys() if unique_pools[0].get('attributes') else 'No attributes'}")
                if unique_pools[0].get('relationships'):
                    logger.info(f"Pool relationships: {unique_pools[0].get('relationships', {}).keys()}")
                self._logged_rug_pool = True
            
            current_time = time.time()
            
            for pool in unique_pools:
                pool_id = pool.get('id')
                if not pool_id:
                    continue
                
                # Get pool attributes
                attrs = pool.get('attributes', {})
                token_symbol = attrs.get('name', 'Unknown')
                
                # Extract contract from relationships - THE ONLY PLACE IT EXISTS
                contract = ''
                relationships = pool.get('relationships', {})
                if relationships:
                    base_token = relationships.get('base_token', {})
                    base_token_data = base_token.get('data', {})
                    base_token_id = base_token_data.get('id', '')
                    
                    if base_token_id and '_' in base_token_id:
                        # Format is "network_contractaddress"
                        contract = base_token_id.split('_', 1)[1]
                        logger.debug(f"Extracted contract {contract} for {token_symbol}")
                    else:
                        logger.error(f"No valid base_token.id for {token_symbol}. Relationships: {relationships}")
                else:
                    logger.error(f"No relationships in pool data for {token_symbol}. Pool keys: {pool.keys()}")
                
                if not contract:
                    logger.error(f"Failed to extract contract for {token_symbol} - skipping")
                    continue
                
                # Skip if already detected recently
                if contract in self.detected_rugs:
                    last_detection = self.detected_rugs[contract].timestamp.timestamp()
                    if current_time - last_detection < self.rug_cooldown:
                        continue
                
                # Get current metrics
                current_liquidity = float(attrs.get('reserve_in_usd', 0))
                if current_liquidity == 0:
                    current_liquidity = float(attrs.get('total_reserve_in_usd', 0))
                
                current_price = float(attrs.get('base_token_price_usd', 0))
                
                # Get 1-hour volume
                volume_data = attrs.get('volume_usd', {})
                if isinstance(volume_data, dict):
                    volume_1h = float(volume_data.get('h1', 0))
                else:
                    # Fallback to direct attribute
                    volume_1h = float(attrs.get('volume_usd_h1', 0))
                
                # Store current data
                pool_data = {
                    'timestamp': current_time,
                    'liquidity': current_liquidity,
                    'price': current_price,
                    'volume_1h': volume_1h,
                    'symbol': token_symbol,
                    'contract': contract
                }
                
                self.pool_history[pool_id].append(pool_data)
                
                # Check for rug indicators
                rug_alert = self._check_rug_indicators(pool_id, pool_data)
                
                if rug_alert:
                    logger.warning(f"RUG DETECTED: {token_symbol} on {network}, contract: '{rug_alert.contract}'")
                    self.stats['rugs_detected'] += 1
                    self.detected_rugs[contract] = rug_alert
                    
                    # Log what we're about to broadcast
                    logger.info(f"Broadcasting rug alert with contract: '{rug_alert.contract}', network: '{network}'")
                    
                    # Format and broadcast alert
                    await self._broadcast_rug_alert(rug_alert, network)
                    
        except Exception as e:
            logger.error(f"Error scanning {network} for rugs: {e}")
    
    
    def _check_rug_indicators(self, pool_id: str, current_data: Dict[str, Any]) -> Optional[RugAlert]:
        """Check for rug pull indicators - compares to 60 seconds ago"""
        if pool_id not in self.pool_history or len(self.pool_history[pool_id]) < 2:
            return None
        
        history = self.pool_history[pool_id]
        current_liquidity = current_data['liquidity']
        current_price = current_data['price']
        current_volume_1h = current_data.get('volume_1h', 0)
        current_time = current_data['timestamp']
        
        # Find record from 60 seconds ago
        target_time = current_time - 60
        historical_record = None
        
        # Sort history by timestamp (newest first)
        sorted_history = sorted(history, key=lambda x: x['timestamp'], reverse=True)
        
        for record in sorted_history:
            if record['timestamp'] <= target_time:
                historical_record = record
                break
        
        if not historical_record:
            return None
            
        # Skip if the data is too old (more than threshold seconds)
        if current_time - historical_record['timestamp'] > MAX_HISTORICAL_DATA_AGE:
            return None
        
        # Calculate changes
        liquidity_change = 0
        if historical_record['liquidity'] > 0:
            liquidity_change = ((historical_record['liquidity'] - current_liquidity) / 
                              historical_record['liquidity']) * 100
        
        price_change = 0
        if historical_record['price'] > 0:
            price_change = ((historical_record['price'] - current_price) / 
                          historical_record['price']) * 100
        
        volume_change = 0
        historical_volume_1h = historical_record.get('volume_1h', 0)
        if historical_volume_1h > 0:
            volume_change = ((current_volume_1h - historical_volume_1h) / 
                           historical_volume_1h) * 100
        
        # Check rug criteria in order: Liquidity → Price → Volume
        
        # 1. LIQUIDITY DRAIN: Check against criteria
        liquidity_criteria = RUG_LIQUIDITY_DRAIN_CRITERIA
        if (liquidity_change >= liquidity_criteria['min_liquidity_drop_percent'] and 
            historical_record['liquidity'] >= liquidity_criteria['min_initial_liquidity'] and 
            current_liquidity < liquidity_criteria['max_final_liquidity']):
            logger.info(f"RUG DETECTED (LIQUIDITY_DRAIN): {current_data['symbol']} - {liquidity_change:.1f}% liquidity drop, final liquidity: ${current_liquidity:.0f}")
            return RugAlert(
                token_symbol=current_data['symbol'],
                contract=current_data['contract'],
                network="",  # Will be set by caller
                liquidity_drain_percent=liquidity_change,
                price_drop_percent=price_change,
                volume_spike_percent=volume_change,
                final_liquidity=current_liquidity,
                final_volume_1h=current_volume_1h,
                timestamp=datetime.utcnow(),
                rug_type=liquidity_criteria['rug_type']
            )
        
        # 2. PRICE CRASH: Check against criteria
        price_criteria = RUG_PRICE_CRASH_CRITERIA
        if price_change >= price_criteria['min_price_drop_percent']:
            logger.info(f"RUG DETECTED (PRICE_CRASH): {current_data['symbol']} - {price_change:.1f}% price drop")
            return RugAlert(
                token_symbol=current_data['symbol'],
                contract=current_data['contract'],
                network="",  # Will be set by caller
                liquidity_drain_percent=liquidity_change,
                price_drop_percent=price_change,
                volume_spike_percent=volume_change,
                final_liquidity=current_liquidity,
                final_volume_1h=current_volume_1h,
                timestamp=datetime.utcnow(),
                rug_type=price_criteria['rug_type']
            )
        
        # 3. VOLUME DUMP: Check against criteria
        volume_criteria = RUG_VOLUME_DUMP_CRITERIA
        if (volume_change >= volume_criteria['min_volume_spike_percent'] and 
            price_change >= volume_criteria['min_price_drop_percent'] and 
            historical_volume_1h >= volume_criteria['min_previous_volume']):
            logger.info(f"RUG DETECTED (VOLUME_DUMP): {current_data['symbol']} - {volume_change:.1f}% volume spike, {price_change:.1f}% price drop")
            return RugAlert(
                token_symbol=current_data['symbol'],
                contract=current_data['contract'],
                network="",  # Will be set by caller
                liquidity_drain_percent=liquidity_change,
                price_drop_percent=price_change,
                volume_spike_percent=volume_change,
                final_liquidity=current_liquidity,
                final_volume_1h=current_volume_1h,
                timestamp=datetime.utcnow(),
                rug_type=volume_criteria['rug_type']
            )
        
        return None
    
    async def _broadcast_rug_alert(self, alert: RugAlert, network: str):
        """Broadcast rug pull alert"""
        try:
            alert.network = network
            logger.info(f"💀 Broadcasting rug alert for {alert.token_symbol} on {alert.network}")
            
            # Format message
            message = self._format_rug_message(alert)
            
            # Create buttons for rug alert with proper contract/network info
            from src.bot.button_handler import ButtonHandler
            button_handler = ButtonHandler(None, None, None, None)
            buttons = button_handler.create_moonshot_buttons(alert.contract, alert.network)
            
            # Broadcast to all active chats with buttons
            alert_context = {
                'type': 'rug',
                'contract': alert.contract,
                'network': alert.network,
                'symbol': alert.token_symbol
            }
            await self.bot_handler.broadcast_alert(message, buttons, alert_context)
            logger.info(f"✅ Rug alert broadcast completed for {alert.token_symbol}")
            
        except Exception as e:
            logger.error(f"❌ Error broadcasting rug alert: {e}")
    
    def _format_rug_message(self, alert: RugAlert) -> str:
        """Format rug pull alert message"""
        network_names = {
            'eth': 'Ethereum',
            'solana': 'Solana',
            'bsc': 'BNB Smart Chain',
            'base': 'Base'
        }
        network_display = network_names.get(alert.network, alert.network.upper())
        
        # Savage lines collection
        savage_lines = [
            # Classic/Dark Humor
            "Welcome to the rug pull club, anon 🤝",
            "Another day, another rug 🧹",
            "F in the chat for the holders 💀",
            "That's gonna leave a mark 📉",
            "Devs said 'GN' forever 🌙",
            "Exit liquidity: Secured ✅",
            
            # Casino/Degen themed
            "Sir, this is a casino 🎰",
            "House always wins 🏠",
            "Thanks for playing! 🎮",
            "Better luck next shitcoin 🎲",
            "Wen refund? Never 📅",
            
            # Philosophical/Sarcastic
            "Nature is healing (your wallet isn't) 🌿",
            "In rug we trust 🙏",
            "Democracy has spoken (devs voted to leave) 🗳️",
            "This is why we can't have nice things 🤷",
            
            # Web3/Crypto specific
            "Not your keys, not your... wait, it's gone anyway 🔑",
            "Decentralized rug pull achieved ✨",
            "Smart contract? More like smart exit 🧠",
            "The real gains were the rugs we found along the way 💭",
            
            # Motivational (ironic)
            "Diamond hands can't save you now 💎",
            "HODL this L 📊",
            "To the core (of the earth) 🌍",
            "Zoom out (it gets worse) 📈",
            
            # Educational
            "Lesson learned: Trust nobody 📚",
            "Tuition paid to Rug University 🎓",
            "Today's lesson: Due diligence 🔍",
            "Class dismissed (with your money) 🏫"
        ]
        
        import random
        savage_line = random.choice(savage_lines)
        
        # Format based on rug type
        if alert.rug_type == "LIQUIDITY_DRAIN":
            return f"""🚨 RUG PULL DETECTED 🚨

{alert.token_symbol}

☠️ {alert.contract} on {network_display}

📉 LP Drain: -{alert.liquidity_drain_percent:.1f}%

💀 Final Liquidity: ${alert.final_liquidity:,.0f}

━━━━━━━━━━━━━━━

⚠️ LP DRAIN: Developer removed {alert.liquidity_drain_percent:.0f}% of the liquidity pool. This is the most common rug method - the dev pulls out the funds backing the token, making it impossible to sell.

{savage_line}"""
        
        elif alert.rug_type == "PRICE_CRASH":
            return f"""🚨 RUG PULL DETECTED 🚨

{alert.token_symbol}

☠️ {alert.contract} on {network_display}

📉 Liquidity Extraction: -{alert.price_drop_percent:.1f}%

💀 Final Liquidity: ${alert.final_liquidity:,.0f}

━━━━━━━━━━━━━━━

⚠️ LIQUIDITY EXTRACTION: Price nuked {alert.price_drop_percent:.0f}% in 60 seconds. Insiders extracted liquidity by dumping their bags on holders. Get rekt.

{savage_line}"""
        
        else:  # VOLUME_DUMP
            return f"""🚨 RUG PULL DETECTED 🚨

{alert.token_symbol}

☠️ {alert.contract} on {network_display}

📉 Volume Spike: +{alert.volume_spike_percent:.0f}%

💀 Price Impact: -{alert.price_drop_percent:.1f}%

━━━━━━━━━━━━━━━

⚠️ MASSIVE DUMP: Trading volume exploded {alert.volume_spike_percent:.0f}% while price crashed {alert.price_drop_percent:.0f}%. This pattern shows coordinated mass selling - multiple wallets dumping simultaneously, starting with jeets and paper hands cause the project is probably ded.

{savage_line}"""
    
    def _cleanup_old_history(self):
        """Keep only last 10 snapshots (10 minutes) per pool"""
        for pool_id in list(self.pool_history.keys()):
            # Keep only the 10 most recent snapshots
            if len(self.pool_history[pool_id]) > 10:
                # Sort by timestamp (newest first) and keep top 10
                sorted_history = sorted(self.pool_history[pool_id], 
                                      key=lambda x: x['timestamp'], 
                                      reverse=True)
                self.pool_history[pool_id] = sorted_history[:10]
            
            # Remove pool if no data
            if not self.pool_history[pool_id]:
                del self.pool_history[pool_id]
    
    def _generate_status_report(self):
        """Generate status report message with buttons"""
        # Use fixed 45 minute period for consistency
        time_period = 45
        
        # Count recent moonshots by tier
        moonshot_counts = self._count_recent_moonshots_by_tier(time_period)
        total_moonshots = sum(moonshot_counts.values())
        
        # Count recent rugs
        rug_count = self._count_recent_rugs(time_period)
        
        # Use the formatter
        from ..bot.message_formatter import MessageFormatter
        message = MessageFormatter.format_status_report(moonshot_counts, rug_count, time_period)
        
        # Create buttons if there are moonshots or rugs
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        buttons_list = []
        
        if total_moonshots > 0:
            buttons_list.append(InlineKeyboardButton("📈 View Moonshots", callback_data="view_moonshots"))
        
        if rug_count > 0:
            buttons_list.append(InlineKeyboardButton("💀 View Rugs", callback_data="view_rugs"))
        
        buttons = None
        if buttons_list:
            buttons = InlineKeyboardMarkup([buttons_list])
        
        return message, buttons
    
    def _count_recent_moonshots_by_tier(self, minutes: int) -> Dict[str, int]:
        """Count moonshots by tier in the last X minutes"""
        cutoff_time = time.time() - (minutes * 60)
        counts = {'POTENTIAL 100X': 0, 'POTENTIAL 10X': 0, 'POTENTIAL 2X': 0}
        
        logger.debug(f"Counting moonshots since {cutoff_time}. Total stored: {len(self.detected_moonshots)}")
        
        for contract, moonshot_alert in self.detected_moonshots.items():
            logger.debug(f"Checking moonshot {contract}: tier={moonshot_alert.tier}, timestamp={moonshot_alert.timestamp}")
            if moonshot_alert.timestamp.timestamp() >= cutoff_time:
                if moonshot_alert.tier in counts:
                    counts[moonshot_alert.tier] += 1
                    logger.debug(f"Counted moonshot {contract} in tier {moonshot_alert.tier}")
        
        logger.debug(f"Final moonshot counts: {counts}")
        return counts
    
    def _count_recent_rugs(self, minutes: int) -> int:
        """Count rug pulls in the last X minutes"""
        cutoff_time = time.time() - (minutes * 60)
        count = 0
        
        for contract, rug_alert in self.detected_rugs.items():
            if rug_alert.timestamp.timestamp() >= cutoff_time:
                count += 1
        
        return count
    
    async def _scan_network_for_moonshots(self, network: str, pool_type: str):
        """Scan network for moonshot opportunities"""
        try:
            all_pools = []
            
            if pool_type == 'trending':
                # Check all timeframes: 5m, 1h, 6h, 24h
                timeframes = ['5m', '1h', '6h', '24h']
                for timeframe in timeframes:
                    logger.debug(f"Checking {network} trending pools for {timeframe}")
                    pools = await self.api_client.get_trending_pools(network, duration=timeframe, limit=20)
                    if pools:
                        # Add timeframe info to each pool
                        for pool in pools:
                            pool['scan_timeframe'] = timeframe
                        all_pools.extend(pools)
            else:  # new
                pools = await self.api_client.get_new_pools(network, limit=30)
                all_pools = pools
            
            if not all_pools:
                logger.warning(f"No {pool_type} pools returned for {network} moonshot monitoring")
                return
            
            # Deduplicate pools by pool_id
            seen_pools = {}
            unique_pools = []
            for pool in all_pools:
                pool_id = pool.get('id')
                if pool_id and pool_id not in seen_pools:
                    seen_pools[pool_id] = True
                    unique_pools.append(pool)
            
            logger.info(f"Checking {len(unique_pools)} unique {pool_type} pools on {network} for moonshots")
            
            current_time = time.time()
            
            for pool in unique_pools:
                pool_id = pool.get('id')
                if not pool_id:
                    continue
                    
                attrs = pool.get('attributes', {})
                token_symbol = attrs.get('name', 'Unknown')
                
                # Extract contract from relationships - THE ONLY PLACE IT EXISTS
                contract = ''
                relationships = pool.get('relationships', {})
                if relationships:
                    base_token = relationships.get('base_token', {})
                    base_token_data = base_token.get('data', {})
                    base_token_id = base_token_data.get('id', '')
                    
                    if base_token_id and '_' in base_token_id:
                        # Format is "network_contractaddress"
                        contract = base_token_id.split('_', 1)[1]
                        logger.debug(f"Extracted contract {contract} for moonshot {token_symbol}")
                    else:
                        logger.error(f"No valid base_token.id for moonshot {token_symbol}")
                else:
                    logger.error(f"No relationships in moonshot pool data for {token_symbol}")
                
                if not contract:
                    logger.error(f"Failed to extract contract for moonshot {token_symbol} - skipping")
                    continue
                
                # Extract and store current pool data for history
                current_price = float(attrs.get('base_token_price_usd', 0))
                current_liquidity = float(attrs.get('reserve_in_usd', 0))
                if current_liquidity == 0:
                    current_liquidity = float(attrs.get('total_reserve_in_usd', 0))
                
                # Store current data in history
                pool_data = {
                    'timestamp': current_time,
                    'price': current_price,
                    'liquidity': current_liquidity,
                    'symbol': token_symbol,
                    'contract': contract,
                    'pool_data': pool  # Store full pool data for analysis
                }
                
                self.pool_history[pool_id].append(pool_data)
                
                # Skip if already detected recently
                if contract in self.detected_moonshots:
                    last_detection = self.detected_moonshots[contract].timestamp.timestamp()
                    if current_time - last_detection < self.moonshot_cooldown:
                        continue
                
                # Check moonshot criteria with historical data
                moonshot_alert = await self._check_moonshot_criteria(pool, network, pool_id)
                
                if moonshot_alert:
                    logger.info(f"MOONSHOT DETECTED: {moonshot_alert.token_symbol} on {network} - {moonshot_alert.tier}")
                    self.stats['moonshots_detected'] += 1
                    self.detected_moonshots[contract] = moonshot_alert
                    
                    # Broadcast alert
                    await self._broadcast_moonshot_alert(moonshot_alert)
                    
        except Exception as e:
            logger.error(f"Error scanning {network} for moonshots: {e}")
    
    async def _check_moonshot_criteria(self, pool: Dict[str, Any], network: str, pool_id: str = None) -> Optional[MoonshotAlert]:
        """Check if pool meets moonshot criteria using historical data"""
        attrs = pool.get('attributes', {})
        
        # Debug log first pool to see data structure
        if not hasattr(self, '_logged_pool_structure'):
            logger.info(f"Pool data structure sample: {list(attrs.keys())[:10]}")
            self._logged_pool_structure = True
        
        # Helper function to safely get float values
        def safe_float(value, default=0):
            if value is None:
                return default
            try:
                return float(value)
            except (TypeError, ValueError):
                return default
        
        # Extract metrics - matching archive structure
        token_symbol = attrs.get('name', 'Unknown')
        
        # Extract contract from relationships - THE ONLY PLACE IT EXISTS
        contract = ''
        if isinstance(pool, dict):
            # Extract from pool relationships
            relationships = pool.get('relationships', {})
            base_token = relationships.get('base_token', {}).get('data', {})
            base_token_id = base_token.get('id', '')
            
            # Format is "network_contractaddress"
            if base_token_id and '_' in base_token_id:
                contract = base_token_id.split('_', 1)[1]
                logger.debug(f"Extracted contract from relationships: {contract}")
        
        # Current metrics
        current_price = safe_float(attrs.get('base_token_price_usd', 0))
        
        # Liquidity can be in different fields
        liquidity = safe_float(attrs.get('reserve_in_usd', 0))
        if liquidity == 0:
            liquidity = safe_float(attrs.get('total_reserve_in_usd', 0))
        
        # Market cap - try different possible fields
        market_cap = safe_float(attrs.get('market_cap_usd', 0))
        if market_cap == 0:
            market_cap = safe_float(attrs.get('fdv_usd', 0))  # Use FDV as fallback
        if market_cap == 0:
            market_cap = safe_float(attrs.get('base_token_market_cap_usd', 0))
        
        # Volume - check nested structure
        volume_data = attrs.get('volume_usd', {})
        if isinstance(volume_data, dict):
            volume_24h = safe_float(volume_data.get('h24', 0))
        else:
            # Fallback to direct attribute
            volume_24h = safe_float(attrs.get('volume_usd_h24', 0))
        
        # Transaction count - check nested structure
        tx_data = attrs.get('transactions', {})
        if isinstance(tx_data, dict):
            h24_data = tx_data.get('h24', {})
            if isinstance(h24_data, dict):
                tx_count_24h = int(h24_data.get('buys', 0)) + int(h24_data.get('sells', 0))
            else:
                tx_count_24h = 0
        else:
            # Fallback
            tx_h24 = attrs.get('transactions_h24', {})
            if isinstance(tx_h24, dict):
                tx_count_24h = int(tx_h24.get('buys', 0)) + int(tx_h24.get('sells', 0))
            else:
                tx_count_24h = 0
        
        # Calculate price changes from historical data if we have pool_id
        price_change_1m = 0
        price_change_5m = 0
        price_change_1h = 0
        price_change_24h = 0
        
        if pool_id and pool_id in self.pool_history:
            history = self.pool_history[pool_id]
            current_time = time.time()
            
            # Calculate price changes for different timeframes
            timeframes = [
                (60, '1m'),     # 1 minute
                (300, '5m'),    # 5 minutes
                (3600, '1h'),   # 1 hour
                (86400, '24h')  # 24 hours
            ]
            
            for seconds_ago, timeframe in timeframes:
                # Find the closest historical record to this timeframe
                target_time = current_time - seconds_ago
                historical_record = None
                
                # Sort history by timestamp (newest first)
                sorted_history = sorted(history, key=lambda x: x['timestamp'], reverse=True)
                
                for record in sorted_history:
                    if record['timestamp'] <= target_time:
                        historical_record = record
                        break
                
                if historical_record and historical_record.get('price', 0) > 0:
                    # Calculate percentage change
                    price_then = historical_record['price']
                    if price_then > 0:
                        change_percent = ((current_price - price_then) / price_then) * 100
                        
                        if timeframe == '1m':
                            price_change_1m = change_percent
                        elif timeframe == '5m':
                            price_change_5m = change_percent
                        elif timeframe == '1h':
                            price_change_1h = change_percent
                        elif timeframe == '24h':
                            price_change_24h = change_percent
                        
                        logger.debug(f"Calculated {timeframe} price change: {change_percent:.2f}% for {token_symbol}")
        else:
            # Fallback to API-provided price changes if no history
            logger.debug(f"No historical data for {token_symbol}, using API price changes")
            
            # Price changes - check nested structure like archive
            price_changes = attrs.get('price_change_percentage', {})
            if isinstance(price_changes, dict):
                price_change_1m = safe_float(price_changes.get('m1', 0))
                price_change_5m = safe_float(price_changes.get('m5', 0))
                price_change_1h = safe_float(price_changes.get('h1', 0))
                price_change_24h = safe_float(price_changes.get('h24', 0))
            else:
                # Fallback to direct attributes
                price_change_1m = safe_float(attrs.get('price_change_percentage_1m', 0))
                price_change_5m = safe_float(attrs.get('price_change_percentage_5m', 0))
                price_change_1h = safe_float(attrs.get('price_change_percentage_h1', 0))
                price_change_24h = safe_float(attrs.get('price_change_percentage_h24', 0))
        
        # Check all timeframes for moonshot criteria
        best_price_change = 0
        best_timeframe = ""
        
        # Find the highest price change across all timeframes
        timeframe_changes = [
            (price_change_1m, "1m"),
            (price_change_5m, "5m"),
            (price_change_1h, "1h"),
            (price_change_24h, "24h")
        ]
        
        for change, timeframe in timeframe_changes:
            if change > best_price_change:
                best_price_change = change
                best_timeframe = timeframe
        
        # Check moonshot criteria using algorithm definitions
        for criteria in MOONSHOT_CRITERIA_LIST:
            if (liquidity >= criteria['min_liquidity'] and 
                best_price_change >= criteria['min_price_change'] and 
                volume_24h >= criteria['min_volume_24h'] and 
                tx_count_24h >= criteria['min_tx_count_24h'] and
                market_cap >= criteria['min_market_cap']):
                
                logger.info(f"{criteria['tier']} MOONSHOT DETECTED: {token_symbol} - {best_price_change:.1f}% in {best_timeframe}, MCap: ${market_cap:,.0f}")
                alert = MoonshotAlert(
                    token_symbol=token_symbol,
                    contract=contract,
                    network=network,
                    tier=criteria['tier'],
                    price_change_percent=best_price_change,
                    volume_24h=volume_24h,
                    liquidity=liquidity,
                    transaction_count=tx_count_24h,
                    timestamp=datetime.utcnow(),
                    price_usd=current_price
                )
                logger.debug(f"Created {criteria['tier']} moonshot alert for {contract} at {alert.timestamp}")
                return alert
        
        return None
    
    async def _broadcast_moonshot_alert(self, alert: MoonshotAlert):
        """Broadcast moonshot alert with buttons"""
        try:
            logger.info(f"🚀 Broadcasting moonshot alert for {alert.token_symbol} on {alert.network}")
            
            self.detected_moonshots[alert.contract] = alert
            logger.debug(f"Stored moonshot alert for {alert.contract} in detected_moonshots. Total: {len(self.detected_moonshots)}")
            
            # Format message
            message = self._format_moonshot_message(alert)
            
            # Create buttons for moonshot alert with proper contract/network info
            from src.bot.button_handler import ButtonHandler
            button_handler = ButtonHandler(None, None, None, None)
            buttons = button_handler.create_moonshot_buttons(alert.contract, alert.network)
            
            # Broadcast to all active chats
            alert_context = {
                'type': 'moonshot',
                'contract': alert.contract,
                'network': alert.network,
                'symbol': alert.token_symbol
            }
            await self.bot_handler.broadcast_alert(message, buttons, alert_context)
            logger.info(f"✅ Moonshot alert broadcast completed for {alert.token_symbol}")
            
        except Exception as e:
            logger.error(f"❌ Error broadcasting moonshot alert: {e}")
    
    def _format_moonshot_message(self, alert: MoonshotAlert) -> str:
        """Format moonshot alert message"""
        network_names = {
            'eth': 'Ethereum',
            'solana': 'Solana', 
            'bsc': 'BNB Smart Chain',
            'base': 'Base'
        }
        network_display = network_names.get(alert.network, alert.network.upper())
        
        config = TIER_CONFIG.get(alert.tier, {"emoji": "🚀", "timeframe": "5m"})
        
        # Get random savage line
        savage_lines = [
            "Don't cry at the casino! 🎰",
            "DYOR or get REKT! 💀",
            "Welcome to the trenches! ⚰️",
            "Ape responsibly! 🦍",
            "This is not financial advice! 🚫",
            "May the odds be ever in your favor! 🎲",
            "Remember: scared money don't make money! 💸"
        ]
        import random
        savage_line = random.choice(savage_lines)
        
        # Format numbers
        if alert.liquidity < 10000:
            liquidity_fmt = f"${alert.liquidity:,.0f}"
        else:
            liquidity_fmt = f"${alert.liquidity/1000:.1f}K"
            
        if alert.volume_24h < 10000:
            volume_fmt = f"${alert.volume_24h:,.0f}"
        else:
            volume_fmt = f"${alert.volume_24h/1000:.1f}K"
        
        return f"""🚨 We found some moonshots while diggin the trenches!

{alert.token_symbol}

{config['emoji']} {alert.tier} Moonshot: {alert.token_symbol}

💰 **Price:** ${alert.price_usd:.8f}

📈 **{config['timeframe']} Change:** +{alert.price_change_percent:.1f}%

💧 **Liquidity:** {liquidity_fmt}

📊 **Volume 24h:** {volume_fmt}

🔥 **Transactions:** {alert.transaction_count}

📱 **Contract:** `{alert.contract}`

🌐 **Network:** {network_display}

{savage_line}

---

🌝 **MOONSHOT TIERS:**

🚀 POTENTIAL 100X = High risk/reward, early explosive moves

⚡ POTENTIAL 10X = Good momentum, medium risk potential

💰 POTENTIAL 2X = Safer plays, steady gains with bigger liquidity

---

⚠️ **WARNING**

Prices can crash as quickly as they soar and high chance of manipulation.

Only invest what you're okay losing, and be ready to pull out fast."""
