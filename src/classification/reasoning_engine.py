"""
BALZ Reasoning Engine - The core classification system
Analyzes tokens based on liquidity, volume, market cap, and FDV ratios
"""

import logging
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass

from src.algorithms.balz_classification import (
    BALZCategory, TierLevel, VOLUME_TIERS, LIQUIDITY_TIERS, 
    MARKET_CAP_TIERS, FDV_TIERS, FDV_RATIO_TIERS, SUB_CATEGORIES
)

from enum import Enum

logger = logging.getLogger(__name__)


class BALZCategory(Enum):
    """BALZ classification categories"""
    TRASH = "TRASH"
    RISKY = "RISKY"
    CAUTION = "CAUTION"
    OPPORTUNITY = "OPPORTUNITY"


class TierLevel(Enum):
    """Generic tier levels for metrics"""
    TIER_1 = 1  # Lowest/Worst
    TIER_2 = 2
    TIER_3 = 3
    TIER_4 = 4
    TIER_5 = 5  # Highest/Best


@dataclass
class TokenClassification:
    """Complete token classification result"""
    category: BALZCategory
    sub_category: Optional[str]
    volume_tier: str
    liquidity_tier: str
    market_cap_tier: str
    fdv_tier: str
    fdv_ratio_tier: str
    confidence_score: float
    reasoning: str
    emoji: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'category': self.category.value,
            'sub_category': self.sub_category,
            'volume_tier': self.volume_tier,
            'liquidity_tier': self.liquidity_tier,
            'market_cap_tier': self.market_cap_tier,
            'fdv_tier': self.fdv_tier,
            'fdv_ratio_tier': self.fdv_ratio_tier,
            'confidence_score': self.confidence_score,
            'reasoning': self.reasoning,
            'emoji': self.emoji
        }


class ReasoningEngine:
    """
    BALZ Classification Engine
    Analyzes tokens based on multiple metrics and assigns categories
    """
    
    def __init__(self):
        """Initialize the reasoning engine with tier definitions from algorithms"""
        
        self.volume_tiers = VOLUME_TIERS
        self.liquidity_tiers = LIQUIDITY_TIERS
        self.market_cap_tiers = MARKET_CAP_TIERS
        self.fdv_tiers = FDV_TIERS
        self.fdv_ratio_tiers = FDV_RATIO_TIERS
        self.sub_categories = SUB_CATEGORIES
        
    def classify_token(self, token_data: Any) -> TokenClassification:
        """
        Main classification method
        
        Args:
            token_data: Token data from API (TokenData.to_dict() or raw dict)
            
        Returns:
            TokenClassification object with complete analysis
        """
        try:
            # Handle both TokenData objects and dicts
            if hasattr(token_data, 'volume_24h'):
                # It's a TokenData object
                volume_24h = float(token_data.volume_24h)
                liquidity = float(token_data.liquidity_usd)
                market_cap = float(token_data.market_cap_usd)
                fdv = float(token_data.fdv_usd)
            else:
                # It's a dict
                volume_24h = float(token_data.get('volume_24h', 0))
                liquidity = float(token_data.get('liquidity_usd', 0))
                market_cap = float(token_data.get('market_cap_usd', 0))
                fdv = float(token_data.get('fdv_usd', 0))
            
            # Calculate tier classifications
            volume_tier = self._classify_metric(volume_24h, self.volume_tiers)
            liquidity_tier = self._classify_metric(liquidity, self.liquidity_tiers)
            market_cap_tier = self._classify_metric(market_cap, self.market_cap_tiers)
            fdv_tier = self._classify_metric(fdv, self.fdv_tiers)
            
            # Calculate FDV ratio
            fdv_ratio = self._calculate_fdv_ratio(fdv, market_cap)
            fdv_ratio_tier = self._classify_metric(fdv_ratio, self.fdv_ratio_tiers)
            
            # Determine BALZ category based on rules
            category = self._determine_balz_category(
                volume_tier, liquidity_tier, fdv_ratio_tier
            )
            
            # Select sub-category
            sub_category = self._select_sub_category(
                category, volume_tier, liquidity_tier, fdv_ratio_tier, market_cap_tier
            )
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence(
                volume_24h, liquidity, market_cap, fdv_ratio
            )
            
            # Generate reasoning
            reasoning = self._generate_reasoning(
                category, volume_tier, liquidity_tier, 
                fdv_ratio_tier, market_cap_tier
            )
            
            # Get emoji for category
            emoji = self._get_category_emoji(category)
            
            return TokenClassification(
                category=category,
                sub_category=sub_category,
                volume_tier=volume_tier,
                liquidity_tier=liquidity_tier,
                market_cap_tier=market_cap_tier,
                fdv_tier=fdv_tier,
                fdv_ratio_tier=fdv_ratio_tier,
                confidence_score=confidence_score,
                reasoning=reasoning,
                emoji=emoji
            )
            
        except Exception as e:
            logger.error(f"Error classifying token: {e}")
            # Return a default CAUTION classification on error
            return TokenClassification(
                category=BALZCategory.CAUTION,
                sub_category="Analysis Error",
                volume_tier="Unknown",
                liquidity_tier="Unknown",
                market_cap_tier="Unknown",
                fdv_tier="Unknown",
                fdv_ratio_tier="Unknown",
                confidence_score=0.0,
                reasoning="Unable to complete analysis due to data issues",
                emoji="⚠️"
            )
    
    def _classify_metric(self, value: float, tier_config: Dict) -> str:
        """Classify a metric value into its tier"""
        for i, (min_val, max_val) in enumerate(tier_config['ranges']):
            if min_val <= value < max_val:
                return tier_config['labels'][i]
        return tier_config['labels'][-1]
    
    def _calculate_fdv_ratio(self, fdv: float, market_cap: float) -> float:
        """Calculate FDV to Market Cap ratio"""
        if market_cap <= 0:
            return float('inf')  # Infinite ratio for zero market cap
        return fdv / market_cap
    
    def _determine_balz_category(self, volume_tier: str, 
                                liquidity_tier: str, 
                                fdv_ratio_tier: str) -> BALZCategory:
        """
        Core BALZ classification logic
        Based on the blueprint rules - ORDER MATTERS!
        """
        # TRASH: Liquidity between Risky and Decent (most restrictive first)
        if liquidity_tier in ['Risky', 'Thin', 'Decent']:
            return BALZCategory.TRASH
        
        # RISKY: Thin+ liquidity + Active+ volume
        elif (liquidity_tier in ['Thin', 'Decent', 'Deep', 'Prime'] and 
              volume_tier in ['Active', 'Hot', 'Explosive']):
            return BALZCategory.RISKY
        
        # CAUTION: Decent+ liquidity + Active+ volume + Caution+ FDV ratio
        elif (liquidity_tier in ['Decent', 'Deep', 'Prime'] and 
              volume_tier in ['Active', 'Hot', 'Explosive'] and
              fdv_ratio_tier in ['Caution', 'Heavy', 'Bloated', 'Red Flag']):
            return BALZCategory.CAUTION
        
        # OPPORTUNITY: Decent+ liquidity + Hot+ volume + Clean FDV ratio
        elif (liquidity_tier in ['Decent', 'Deep', 'Prime'] and
              volume_tier in ['Hot', 'Explosive'] and
              fdv_ratio_tier == 'Clean'):
            return BALZCategory.OPPORTUNITY
        
        # Default fallback
        else:
            return BALZCategory.CAUTION
    
    def _select_sub_category(self, category: BALZCategory,
                           volume_tier: str,
                           liquidity_tier: str,
                           fdv_ratio_tier: str,
                           market_cap_tier: str) -> Optional[str]:
        """Select appropriate sub-category based on metrics"""
        if category == BALZCategory.TRASH:
            # Dead Pool: Dead/Struggling volume + Decent/Deep/Prime liquidity
            if (volume_tier in ['Dead', 'Struggling'] and 
                liquidity_tier in ['Decent', 'Deep', 'Prime']):
                return "Dead Pool"
            
            # Rug Setup: Any volume + Red Flag FDV ratio
            if fdv_ratio_tier == 'Red Flag':
                return "Rug Setup"
            
            # Pump & Dump Trap: Hot/Explosive volume + Risky/Thin liquidity
            if (volume_tier in ['Hot', 'Explosive'] and 
                liquidity_tier in ['Risky', 'Thin']):
                return "Pump & Dump Trap"
            
            # Shit Coin: Dead volume + Risky liquidity + Mid/Large market cap
            if (volume_tier == 'Dead' and 
                liquidity_tier == 'Risky' and 
                market_cap_tier in ['Mid', 'Large']):
                return "Shit Coin"
            
            return None
                
        elif category == BALZCategory.RISKY:
            # Diluted: Active+ volume + Heavy FDV ratio
            if (volume_tier in ['Active', 'Hot', 'Explosive'] and 
                fdv_ratio_tier == 'Heavy'):
                return "Diluted"
            
            # Over Valued: Struggling volume + Large market cap
            if (volume_tier == 'Struggling' and 
                market_cap_tier == 'Large'):
                return "Over Valued"
            
            # Liquidity Exit Trap: Hot volume + Deep/Prime liquidity + Red Flag FDV
            if (volume_tier == 'Hot' and 
                liquidity_tier in ['Deep', 'Prime'] and 
                fdv_ratio_tier == 'Red Flag'):
                return "Liquidity Exit Trap"
            
            return None
                
        elif category == BALZCategory.CAUTION:
            # Gamble: Dead/Struggling volume + Nano/Micro market cap + Clean FDV
            if (volume_tier in ['Dead', 'Struggling'] and 
                market_cap_tier in ['Nano', 'Micro'] and 
                fdv_ratio_tier == 'Clean'):
                return "Gamble"
            
            # Low-Key Gem: Active volume + Small market cap + Clean FDV + Decent+ liquidity
            if (volume_tier == 'Active' and 
                market_cap_tier == 'Small' and 
                fdv_ratio_tier == 'Clean' and
                liquidity_tier in ['Decent', 'Deep', 'Prime']):
                return "Low-Key Gem"
            
            return None
                
        elif category == BALZCategory.OPPORTUNITY:
            # Gem: Hot volume + Small/Medium market cap + Clean FDV + Deep/Prime liquidity
            if (volume_tier == 'Hot' and 
                market_cap_tier in ['Small', 'Medium'] and 
                fdv_ratio_tier == 'Clean' and 
                liquidity_tier in ['Deep', 'Prime']):
                return "Gem"
            
            # Moonshot: Hot/Explosive volume + Small market cap + Clean FDV + Decent+ liquidity
            if (volume_tier in ['Hot', 'Explosive'] and 
                market_cap_tier == 'Small' and 
                fdv_ratio_tier == 'Clean' and 
                liquidity_tier in ['Decent', 'Deep', 'Prime']):
                return "Moonshot"
            
            return None
                
        return None
    
    def _calculate_confidence(self, volume: float, liquidity: float,
                            market_cap: float, fdv_ratio: float) -> float:
        """
        Calculate confidence score (0.0 to 1.0)
        Based on data quality and consistency
        """
        confidence = 0.0
        
        # Volume confidence
        if volume > 10000:
            confidence += 0.25
        elif volume > 1000:
            confidence += 0.15
            
        # Liquidity confidence
        if liquidity > 100000:
            confidence += 0.25
        elif liquidity > 25000:
            confidence += 0.15
            
        # Market cap confidence
        if market_cap > 1000000:
            confidence += 0.25
        elif market_cap > 100000:
            confidence += 0.15
            
        # FDV ratio confidence (lower is better)
        if fdv_ratio < 2.0:
            confidence += 0.25
        elif fdv_ratio < 5.0:
            confidence += 0.15
            
        return min(confidence, 1.0)
    
    def _generate_reasoning(self, category: BALZCategory,
                          volume_tier: str,
                          liquidity_tier: str,
                          fdv_ratio_tier: str,
                          market_cap_tier: str) -> str:
        """Generate reasoning text for the classification"""
        if category == BALZCategory.TRASH:
            return (f"This token shows critical red flags with {liquidity_tier} liquidity "
                   f"and {volume_tier} volume. The {fdv_ratio_tier} FDV ratio suggests "
                   f"extreme caution is needed.")
                   
        elif category == BALZCategory.RISKY:
            return (f"High-risk token with {liquidity_tier} liquidity and {volume_tier} volume. "
                   f"The {fdv_ratio_tier} FDV ratio indicates significant volatility potential.")
                   
        elif category == BALZCategory.CAUTION:
            return (f"Mixed signals with {liquidity_tier} liquidity and {volume_tier} volume. "
                   f"The {fdv_ratio_tier} FDV ratio suggests careful consideration needed.")
                   
        elif category == BALZCategory.OPPORTUNITY:
            return (f"Strong potential with {liquidity_tier} liquidity and {volume_tier} volume. "
                   f"The {fdv_ratio_tier} FDV ratio indicates healthy tokenomics.")
                   
        return "Classification analysis complete."
    
    def _get_category_emoji(self, category: BALZCategory) -> str:
        """Get emoji for category"""
        emoji_map = {
            BALZCategory.TRASH: "⛔",
            BALZCategory.RISKY: "🙅🏻‍♂️",
            BALZCategory.CAUTION: "⚠️",
            BALZCategory.OPPORTUNITY: "🚀"
        }
        return emoji_map.get(category, "❓")
    
    def get_tier_value(self, tier_label: str, tier_config: Dict) -> int:
        """Get numeric tier value (1-5) for a label"""
        try:
            return tier_config['labels'].index(tier_label) + 1
        except ValueError:
            return 0
