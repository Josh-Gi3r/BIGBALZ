"""
BALZ Classification System - Proprietary Algorithm
Contains secret sauce tier definitions and scoring logic
"""

from enum import Enum

class BALZCategory(Enum):
    TRASH = "TRASH"
    RISKY = "RISKY" 
    CAUTION = "CAUTION"
    OPPORTUNITY = "OPPORTUNITY"

class TierLevel(Enum):
    VERY_LOW = "Very Low"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    VERY_HIGH = "Very High"

# Volume tiers (24h trading activity in USD)
VOLUME_TIERS = {
    'ranges': [
        (0, 1000),           # Dead
        (1000, 10000),       # Struggling
        (10000, 100000),     # Active
        (100000, 1000000),   # Hot
        (1000000, float('inf'))  # Explosive
    ],
    'labels': ['Dead', 'Struggling', 'Active', 'Hot', 'Explosive']
}

# Liquidity tiers (DEX pool depth in USD)
LIQUIDITY_TIERS = {
    'ranges': [
        (0, 25000),          # Risky
        (25000, 100000),     # Thin
        (100000, 300000),    # Decent
        (300000, 1000000),   # Deep
        (1000000, float('inf'))  # Prime
    ],
    'labels': ['Risky', 'Thin', 'Decent', 'Deep', 'Prime']
}

# Market cap tiers (in USD)
MARKET_CAP_TIERS = {
    'ranges': [
        (0, 100000),         # Nano
        (100000, 1000000),   # Micro
        (1000000, 10000000), # Small
        (10000000, 100000000), # Mid
        (100000000, float('inf'))  # Large
    ],
    'labels': ['Nano', 'Micro', 'Small', 'Mid', 'Large']
}

# FDV tiers (Fully Diluted Valuation in USD)
FDV_TIERS = {
    'ranges': [
        (0, 500000),         # Micro
        (500000, 5000000),   # Small
        (5000000, 50000000), # Medium
        (50000000, 500000000), # Large
        (500000000, float('inf'))  # Maxxed
    ],
    'labels': ['Micro', 'Small', 'Medium', 'Large', 'Maxxed']
}

# FDV/MC ratio tiers (tokenomics health)
FDV_RATIO_TIERS = {
    'ranges': [
        (1.0, 1.5),          # Clean
        (1.5, 3.0),          # Caution
        (3.0, 7.0),          # Heavy
        (7.0, 10.0),         # Bloated
        (10.0, float('inf')) # Red Flag
    ],
    'labels': ['Clean', 'Caution', 'Heavy', 'Bloated', 'Red Flag']
}

# Sub-category mappings for more specific classifications
SUB_CATEGORIES = {
    BALZCategory.TRASH: ['Rug Setup', 'Exit Liquidity', 'Dead Project', 'Scam Alert'],
    BALZCategory.RISKY: ['Degen Play', 'High Risk High Reward', 'Gamble Territory'],
    BALZCategory.CAUTION: ['Mixed Signals', 'Needs Research', 'Watch Carefully'],
    BALZCategory.OPPORTUNITY: ['Hidden Gem', 'Early Entry', 'Strong Fundamentals']
}
