"""
Whale Tracker for BIGBALZ Bot
Analyzes large holder activity and calculates confidence scores
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from .geckoterminal_client import GeckoTerminalClient
from ..bot.message_formatter import MessageFormatter

logger = logging.getLogger(__name__)


class WhaleTracker:
    """
    Tracks and analyzes whale (large holder) activity
    Provides confidence scoring based on whale behavior
    """
    
    def __init__(self, api_client: GeckoTerminalClient):
        """
        Initialize whale tracker
        
        Args:
            api_client: GeckoTerminal API client instance
        """
        self.api_client = api_client
        
        # Whale thresholds as percentage of total supply
        self.whale_thresholds = {
            'mega_whale': 5.0,    # 5%+ of supply
            'large_whale': 2.0,   # 2-5% of supply
            'medium_whale': 1.0,  # 1-2% of supply
            'small_whale': 0.5    # 0.5-1% of supply
        }
        
    async def analyze_whales(self, network: str, contract: str,
                           token_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Analyze whale activity for a token
        
        Args:
            network: Network identifier
            contract: Contract address
            token_data: Token data from API
            
        Returns:
            Whale analysis data or None if unavailable
        """
        try:
            # Get pool address from token data
            pool_address = self._get_primary_pool_address(token_data)
            if not pool_address:
                logger.warning(f"No pool address found for {contract}")
                return None
            
            # Fetch recent trades
            trades = await self.api_client.get_whale_trades(network, pool_address, limit=100)
            if not trades:
                logger.warning(f"No trade data available for {contract}")
                return None
            
            # Analyze whale holdings and activity
            whale_data = self._analyze_whale_holdings(trades, token_data)
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(whale_data)
            
            # Format final analysis
            return {
                'whale_count': whale_data['whale_count'],
                'total_whale_percentage': whale_data['total_percentage'],
                'top_whales': whale_data['top_whales'],
                'confidence_score': confidence_score,
                'buy_sell_ratio': whale_data['buy_sell_ratio'],
                'recent_whale_activity': whale_data['recent_activity'],
                'risk_level': self._determine_risk_level(confidence_score)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing whales: {e}")
            return None
    
    def _get_primary_pool_address(self, token_data: Dict[str, Any]) -> Optional[str]:
        """Extract primary pool address from token data"""
        # Direct pool_address field from TokenData
        if isinstance(token_data, dict) and 'pool_address' in token_data:
            return token_data['pool_address']
        
        # Fallback for other data structures
        if isinstance(token_data, dict):
            if 'primary_pool' in token_data:
                return token_data['primary_pool']
            # If we have relationships data
            if 'relationships' in token_data:
                pools = token_data.get('relationships', {}).get('top_pools', {}).get('data', [])
                if pools:
                    return pools[0].get('id')
        
        return None
    
    def _analyze_whale_holdings(self, trades: List[Dict[str, Any]], 
                              token_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze whale holdings from trade data"""
        # Track unique addresses and their activity
        address_activity = defaultdict(lambda: {
            'total_volume': 0,
            'buy_volume': 0,
            'sell_volume': 0,
            'last_action': None,
            'last_timestamp': None,
            'trade_count': 0
        })
        
        # Process trades
        for trade in trades:
            address = trade.get('from_address', '').lower()
            if not address:
                continue
            
            volume = trade.get('amount_usd', 0)
            trade_type = trade.get('type', 'unknown')
            timestamp = trade.get('timestamp')
            
            # Update address activity
            activity = address_activity[address]
            activity['total_volume'] += volume
            activity['trade_count'] += 1
            
            if trade_type == 'buy':
                activity['buy_volume'] += volume
            elif trade_type == 'sell':
                activity['sell_volume'] += volume
            
            # Track last action
            if timestamp:
                if not activity['last_timestamp'] or timestamp > activity['last_timestamp']:
                    activity['last_action'] = trade_type.upper()
                    activity['last_timestamp'] = timestamp
        
        # Identify whales based on volume
        whales = []
        total_volume = sum(a['total_volume'] for a in address_activity.values())
        
        for address, activity in address_activity.items():
            # Calculate percentage of total volume
            percentage = (activity['total_volume'] / total_volume * 100) if total_volume > 0 else 0
            
            # Consider as whale if significant volume
            if percentage >= 0.5:  # 0.5% of total volume
                whale_data = {
                    'address': address,
                    'percentage': percentage,
                    'total_volume': activity['total_volume'],
                    'buy_volume': activity['buy_volume'],
                    'sell_volume': activity['sell_volume'],
                    'last_activity': activity['last_action'] or 'HOLD',
                    'trade_count': activity['trade_count'],
                    'net_position': activity['buy_volume'] - activity['sell_volume']
                }
                whales.append(whale_data)
        
        # Sort by percentage
        whales.sort(key=lambda x: x['percentage'], reverse=True)
        
        # Calculate aggregate metrics
        total_whale_percentage = sum(w['percentage'] for w in whales)
        total_buy_volume = sum(w['buy_volume'] for w in whales)
        total_sell_volume = sum(w['sell_volume'] for w in whales)
        
        # Buy/sell ratio
        buy_sell_ratio = (total_buy_volume / total_sell_volume 
                         if total_sell_volume > 0 else float('inf'))
        
        # Recent activity (last 24h)
        recent_activity = self._analyze_recent_activity(trades)
        
        return {
            'whale_count': len(whales),
            'total_percentage': total_whale_percentage,
            'top_whales': whales[:10],  # Top 10 whales
            'buy_sell_ratio': buy_sell_ratio,
            'recent_activity': recent_activity,
            'total_buy_volume': total_buy_volume,
            'total_sell_volume': total_sell_volume
        }
    
    def _analyze_recent_activity(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze recent whale activity (last 24h)"""
        now = datetime.utcnow()
        cutoff = now - timedelta(hours=24)
        
        recent_buys = 0
        recent_sells = 0
        recent_volume = 0
        
        for trade in trades:
            timestamp = trade.get('timestamp')
            if not timestamp:
                continue
            
            # Parse timestamp (assuming ISO format)
            try:
                trade_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                if trade_time < cutoff:
                    continue
                
                volume = trade.get('amount_usd', 0)
                trade_type = trade.get('type', 'unknown')
                
                recent_volume += volume
                if trade_type == 'buy':
                    recent_buys += 1
                elif trade_type == 'sell':
                    recent_sells += 1
                    
            except Exception as e:
                logger.debug(f"Error parsing timestamp: {e}")
                continue
        
        return {
            'recent_buys': recent_buys,
            'recent_sells': recent_sells,
            'recent_volume': recent_volume,
            'buy_pressure': recent_buys > recent_sells * 1.5,
            'sell_pressure': recent_sells > recent_buys * 1.5
        }
    
    def _calculate_confidence_score(self, whale_data: Dict[str, Any]) -> float:
        """
        Calculate confidence score (0-10) based on whale behavior
        
        Factors:
        - Number of whales (diversity)
        - Total whale holdings percentage
        - Buy/sell ratio
        - Recent activity patterns
        - Position concentration
        """
        score = 5.0  # Start at neutral
        
        # Factor 1: Whale diversity (more whales = better)
        whale_count = whale_data['whale_count']
        if whale_count >= 10:
            score += 1.0
        elif whale_count >= 5:
            score += 0.5
        elif whale_count <= 2:
            score -= 1.0
        
        # Factor 2: Total holdings (moderate is best)
        total_percentage = whale_data['total_whale_percentage']
        if 20 <= total_percentage <= 40:
            score += 1.0  # Healthy range
        elif total_percentage < 20:
            score += 0.5  # Good distribution
        elif total_percentage > 60:
            score -= 2.0  # Too concentrated
        elif total_percentage > 50:
            score -= 1.0
        
        # Factor 3: Buy/sell ratio
        buy_sell_ratio = whale_data['buy_sell_ratio']
        if buy_sell_ratio > 2.0:
            score += 1.5  # Strong buying
        elif buy_sell_ratio > 1.5:
            score += 1.0
        elif buy_sell_ratio > 1.0:
            score += 0.5
        elif buy_sell_ratio < 0.5:
            score -= 1.5  # Heavy selling
        elif buy_sell_ratio < 0.75:
            score -= 1.0
        
        # Factor 4: Recent activity
        recent = whale_data['recent_activity']
        if recent['buy_pressure']:
            score += 1.0
        elif recent['sell_pressure']:
            score -= 1.0
        
        # Factor 5: Top whale concentration
        if whale_data['top_whales']:
            top_whale_percentage = whale_data['top_whales'][0]['percentage']
            if top_whale_percentage > 20:
                score -= 1.5  # Single whale too dominant
            elif top_whale_percentage > 15:
                score -= 0.5
        
        # Ensure score is within 0-10 range
        return max(0, min(10, score))
    
    def _determine_risk_level(self, confidence_score: float) -> str:
        """Determine risk level based on confidence score"""
        if confidence_score >= 7:
            return "LOW"
        elif confidence_score >= 4:
            return "MEDIUM"
        else:
            return "HIGH"
    
    def format_whale_response(self, whale_data: Dict[str, Any], 
                            token_name: str) -> str:
        """
        Format whale analysis response
        
        Args:
            whale_data: Whale analysis data
            token_name: Token name and symbol
            
        Returns:
            Formatted response string
        """
        return MessageFormatter.format_whale_analysis(whale_data, token_name)