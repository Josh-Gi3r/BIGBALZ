"""
Message Formatter for BIGBALZ Bot
Handles all message formatting for consistent output
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..utils.validators import ContractValidator
from ..api.geckoterminal_client import TokenData

logger = logging.getLogger(__name__)


class MessageFormatter:
    """
    Formats messages for Telegram display
    Ensures consistent formatting across all bot responses
    """
    
    @staticmethod
    def format_token_overview(token_data: TokenData) -> str:
        """
        Format main token overview message
        
        Args:
            token_data: TokenData object from API
            
        Returns:
            Formatted message string
        """
        # Format numbers appropriately
        price = MessageFormatter._format_price(token_data.price_usd)
        market_cap = MessageFormatter._format_large_number(token_data.market_cap_usd)
        fdv = MessageFormatter._format_large_number(token_data.fdv_usd)
        volume = MessageFormatter._format_large_number(token_data.volume_24h)
        liquidity = MessageFormatter._format_large_number(token_data.liquidity_usd)
        
        # Format contract address
        contract_display = ContractValidator.format_contract_display(token_data.contract_address)
        
        # Get network display name
        from src.utils.network_detector import NetworkDetector
        network_name = NetworkDetector.format_network_name(token_data.network)
        
        # Build the message
        message = f"""🪙 **Token Overview: {token_data.name} ({token_data.symbol})**

💰 **Price:** ${price}

📊 **Market Cap:** {market_cap}

🔢 **FDV:** {fdv}

📦 **Total Supply:** {MessageFormatter._format_supply(token_data.total_supply, token_data.symbol)}

📈 **Volume (24h):** {volume}

💧 **Liquidity:** {liquidity}

**DEX:** {token_data.primary_dex}

**Pair:** {token_data.symbol}/USDT

📱 **Contract:** `{contract_display}`

🌐 **Network:** {network_name}"""

        # Add price changes if available
        if token_data.price_change_24h != 0:
            changes = MessageFormatter._format_price_changes(token_data)
            message += f"\n\n{changes}"
        
        return message
    
    @staticmethod
    def format_moonshot_alert(tier: str, token_data: TokenData, 
                            pool_data: Dict[str, Any]) -> str:
        """
        Format moonshot alert message
        
        Args:
            tier: Moonshot tier (POTENTIAL 100X, POTENTIAL 10X, POTENTIAL 2X)
            token_data: Token information
            pool_data: Pool information
            
        Returns:
            Formatted alert message
        """
        # Determine emoji and timeframe based on tier
        tier_config = {
            'POTENTIAL 100X': ('🚀', '5m'),
            'POTENTIAL 10X': ('⚡', '1h'),
            'POTENTIAL 2X': ('💰', '24h')
        }
        emoji, timeframe = tier_config.get(tier, ('🚀', '5m'))
        
        # Get price change based on tier
        price_change = {
            'POTENTIAL 100X': token_data.price_change_5m,
            'POTENTIAL 10X': token_data.price_change_1h,
            'POTENTIAL 2X': token_data.price_change_24h
        }.get(tier, 0)
        
        # Format numbers
        price = MessageFormatter._format_price(token_data.price_usd)
        liquidity = MessageFormatter._format_large_number(token_data.liquidity_usd)
        volume = MessageFormatter._format_large_number(token_data.volume_24h)
        contract_display = ContractValidator.format_contract_display(token_data.contract_address)
        network_name = ContractValidator.get_network_name(token_data.network)
        
        # Get buy/sell counts from pool data
        buys = pool_data.get('buy_count_24h', 0)
        sells = pool_data.get('sell_count_24h', 0)
        
        return f"""🚨 **{emoji} {tier} Moonshot: {token_data.name} ({token_data.symbol})**

💰 **Price:** ${price}
📈 **{timeframe} Change:** +{price_change:.1f}%
💧 **Liquidity:** {liquidity}
📊 **Volume (24h):** {volume}
🔥 **Buys:** {buys} | **Sells:** {sells}

📱 **Contract:** `{contract_display}`
🌐 **Network:** {network_name}

⚠️ Don't cry at the casino! 🎰"""
    
    @staticmethod
    def format_rug_alert(token_name: str, token_symbol: str,
                        network: str, liquidity_drop: float,
                        final_liquidity: float) -> str:
        """
        Format rug pull alert message
        
        Args:
            token_name: Token name
            token_symbol: Token symbol
            network: Network name
            liquidity_drop: Percentage drop in liquidity
            final_liquidity: Final liquidity amount
            
        Returns:
            Formatted rug alert
        """
        network_name = ContractValidator.get_network_name(network)
        final_liq = MessageFormatter._format_large_number(final_liquidity)
        
        # Random harsh comments
        comments = [
            "Another one bites the dust! 💸",
            "Hope you didn't buy the top! 🤡",
            "Exit liquidity has left the building! 🏃‍♂️",
            "Devs are probably on a beach now! 🏖️",
            "F in the chat for the bagholders! 💀"
        ]
        
        import random
        comment = random.choice(comments)
        
        return f"""🚨 **RUG PULL DETECTED** 🚨

{token_name} ({token_symbol})

☠️ {token_symbol} on {network_name}

📉 **Liquidity Drain:** -{liquidity_drop:.1f}%

💀 **Final Liquidity:** {final_liq}

{comment}"""
    
    @staticmethod
    def format_status_report(moonshot_count, rug_count: int, 
                           time_period: int = 45) -> str:
        """
        Format status report message
        
        Args:
            moonshot_count: Number of moonshots detected
            rug_count: Number of rugs detected
            time_period: Time period in minutes
            
        Returns:
            Formatted status report
        """
        # Get random hunting status line
        hunting_lines = [
            "Still hunting for the next gem...",
            "Scanning the trenches for diamonds...",
            "Separating gems from garbage...",
            "Hunting down the next moonshot...",
            "Keeping watch for opportunities...",
            "Sifting through the noise for signals...",
            "Digging through the degen plays...",
            "On the prowl for the next 100x..."
        ]
        import random
        status_line = random.choice(hunting_lines)
        
        # Calculate total pools scanned (3 networks × 20 pools × scans per minute)
        total_pools = 3 * 20 * time_period
        
        # Handle both dict and int for moonshot_count
        if isinstance(moonshot_count, dict):
            moonshot_100x = moonshot_count.get('100x', 0)
            moonshot_10x = moonshot_count.get('10x', 0)
            moonshot_2x = moonshot_count.get('2x', 0)
        else:
            # Legacy support
            moonshot_100x = moonshot_count
            moonshot_10x = 0
            moonshot_2x = 0
        
        return f"""🔍 **Scanning Report (Last {time_period} min)**

Monitored {total_pools:,} pools across SOL, ETH, Base

Moonshots Found:

🚀 {moonshot_100x} × POTENTIAL 100X

⚡ {moonshot_10x} × POTENTIAL 10X

💰 {moonshot_2x} × POTENTIAL 2X

Rugs Detected:

☠️ {rug_count} × Rug Pulls

{status_line}"""
    
    @staticmethod
    def format_error_message(error_type: str, details: Optional[str] = None) -> str:
        """
        Format error messages
        
        Args:
            error_type: Type of error
            details: Additional error details
            
        Returns:
            Formatted error message
        """
        base_errors = {
            'invalid_contract': "❌ **Invalid Contract Address**\n\nPlease provide a valid contract address for supported networks.",
            'token_not_found': "❌ **Token Not Found**\n\nThe token could not be found on this network.",
            'api_error': "❌ **API Error**\n\nUnable to fetch token data. Please try again later.",
            'rate_limit': "⏰ **Rate Limited**\n\nToo many requests. Please wait a moment.",
            'session_expired': "⏰ **Session Expired**\n\nPlease send a new contract address.",
            'unknown': "❌ **Error**\n\nSomething went wrong. Please try again."
        }
        
        message = base_errors.get(error_type, base_errors['unknown'])
        
        if details:
            message += f"\n\n{details}"
        
        return message
    
    @staticmethod
    def _format_price(price: float) -> str:
        """Format price based on magnitude"""
        if price >= 1:
            return f"{price:,.2f}"
        elif price >= 0.01:
            return f"{price:.4f}"
        elif price >= 0.0001:
            return f"{price:.6f}"
        else:
            return f"{price:.8f}"
    
    @staticmethod
    def _format_large_number(num: float) -> str:
        """Format large numbers with appropriate units"""
        if num >= 1_000_000_000:
            return f"${num/1_000_000_000:.2f}B"
        elif num >= 1_000_000:
            return f"${num/1_000_000:.2f}M"
        elif num >= 1_000:
            return f"${num/1_000:.2f}K"
        else:
            return f"${num:.2f}"
    
    @staticmethod
    def _format_supply(supply: str, symbol: str) -> str:
        """Format token supply"""
        try:
            supply_float = float(supply)
            if supply_float >= 1_000_000_000_000:
                formatted = f"{supply_float/1_000_000_000_000:.2f}T"
            elif supply_float >= 1_000_000_000:
                formatted = f"{supply_float/1_000_000_000:.2f}B"
            elif supply_float >= 1_000_000:
                formatted = f"{supply_float/1_000_000:.2f}M"
            else:
                formatted = f"{supply_float:,.0f}"
            return f"{formatted} {symbol}"
        except:
            return f"{supply} {symbol}"
    
    @staticmethod
    def _format_price_changes(token_data: TokenData) -> str:
        """Format price change section"""
        changes = []
        
        if token_data.price_change_5m != 0:
            emoji = "📈" if token_data.price_change_5m > 0 else "📉"
            changes.append(f"{emoji} **5m:** {token_data.price_change_5m:+.1f}%")
        
        if token_data.price_change_1h != 0:
            emoji = "📈" if token_data.price_change_1h > 0 else "📉"
            changes.append(f"{emoji} **1h:** {token_data.price_change_1h:+.1f}%")
        
        if token_data.price_change_24h != 0:
            emoji = "📈" if token_data.price_change_24h > 0 else "📉"
            changes.append(f"{emoji} **24h:** {token_data.price_change_24h:+.1f}%")
        
        if changes:
            return "**Price Changes:**\n" + " | ".join(changes)
        
        return ""
    
    @staticmethod
    def format_whale_analysis(whale_data: Dict[str, Any], token_name: str) -> str:
        """
        Format whale analysis response
        
        Args:
            whale_data: Whale analysis data
            token_name: Token name and symbol
            
        Returns:
            Formatted whale analysis
        """
        confidence = whale_data.get('confidence_score', 0)
        whale_count = whale_data.get('whale_count', 0)
        total_whale_holdings = whale_data.get('total_whale_percentage', 0)
        
        # Format confidence emoji
        if confidence >= 7:
            conf_emoji = "🟢"
            conf_text = "High Confidence"
        elif confidence >= 4:
            conf_emoji = "🟡"
            conf_text = "Medium Confidence"
        else:
            conf_emoji = "🔴"
            conf_text = "Low Confidence"
        
        message = f"""🐋 **Whale Tracker: {token_name}**

{conf_emoji} **Confidence Score:** {confidence}/10 ({conf_text})

🐳 **Total Whales:** {whale_count}

💰 **Whale Holdings:** {total_whale_holdings:.1f}% of supply

**Top 5 Whales:**"""
        
        # Add individual whale data
        whales = whale_data.get('top_whales', [])
        for i, whale in enumerate(whales[:5], 1):
            address = whale.get('address', 'Unknown')
            address_display = f"{address[:6]}...{address[-4:]}" if len(address) > 10 else address
            holdings = whale.get('percentage', 0)
            activity = whale.get('last_activity', 'UNKNOWN')
            
            activity_emoji = {
                'BUY': '🟢',
                'SELL': '🔴',
                'HOLD': '⏸️'
            }.get(activity, '❓')
            
            message += f"\n{i}. `{address_display}` - {holdings:.2f}% {activity_emoji}"
        
        # Add analysis summary
        if confidence >= 7:
            summary = "\n\n✅ **Healthy whale distribution with positive sentiment**"
        elif confidence >= 4:
            summary = "\n\n⚠️ **Mixed signals - monitor whale movements closely**"
        else:
            summary = "\n\n🚨 **High concentration risk - potential dump warning**"
        
        message += summary
        
        return message