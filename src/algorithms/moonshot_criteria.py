"""
Moonshot Detection Criteria - Proprietary Algorithm
Contains secret sauce thresholds for moonshot classification
"""

MOONSHOT_100X_CRITERIA = {
    'min_liquidity': 10000,
    'min_price_change': 75,
    'min_volume_24h': 15000,
    'min_tx_count_24h': 75,
    'min_market_cap': 50000,
    'tier': 'POTENTIAL 100X',
    'emoji': '🚀',
    'timeframe': '5m'
}

MOONSHOT_10X_CRITERIA = {
    'min_liquidity': 20000,
    'min_price_change': 30,
    'min_volume_24h': 30000,
    'min_tx_count_24h': 100,
    'min_market_cap': 100000,
    'tier': 'POTENTIAL 10X',
    'emoji': '⚡',
    'timeframe': '1h'
}

MOONSHOT_2X_CRITERIA = {
    'min_liquidity': 75000,
    'min_price_change': 20,
    'min_volume_24h': 75000,
    'min_tx_count_24h': 150,
    'min_market_cap': 500000,
    'tier': 'POTENTIAL 2X',
    'emoji': '💰',
    'timeframe': '24h'
}

TIER_CONFIG = {
    "POTENTIAL 100X": {"emoji": "🚀", "timeframe": "5m"},
    "POTENTIAL 10X": {"emoji": "⚡", "timeframe": "1h"},
    "POTENTIAL 2X": {"emoji": "💰", "timeframe": "24h"}
}

MOONSHOT_CRITERIA_LIST = [
    MOONSHOT_100X_CRITERIA,
    MOONSHOT_10X_CRITERIA,
    MOONSHOT_2X_CRITERIA
]
