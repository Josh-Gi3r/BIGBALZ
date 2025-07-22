"""
Gem Research Risk Scoring - Proprietary Algorithm
Contains secret sauce scoring logic for gem risk assessment
"""

GEM_RISK_SCORING = {
    'max_score': 10,  # Maximum risk score (lowest risk)
    
    # Liquidity factor (0-3 points)
    'liquidity_tiers': [
        {'min_value': 1000000, 'points': 3},  # $1M+
        {'min_value': 300000, 'points': 2},   # $300K+
        {'min_value': 100000, 'points': 1},   # $100K+
        {'min_value': 0, 'points': 0}         # Below $100K
    ],
    
    # Volume factor (0-2 points)
    'volume_tiers': [
        {'min_value': 100000, 'points': 2},   # $100K+
        {'min_value': 10000, 'points': 1},    # $10K+
        {'min_value': 0, 'points': 0}         # Below $10K
    ],
    
    # Market cap factor (0-2 points)
    'market_cap_tiers': [
        {'min_value': 10000000, 'points': 2}, # $10M+
        {'min_value': 1000000, 'points': 1},  # $1M+
        {'min_value': 0, 'points': 0}         # Below $1M
    ],
    
    # FDV/MCap ratio factor (0-2 points)
    'fdv_ratio_tiers': [
        {'max_ratio': 2, 'points': 2},        # Ratio < 2
        {'max_ratio': 5, 'points': 1},        # Ratio < 5
        {'max_ratio': float('inf'), 'points': 0}  # Ratio >= 5
    ],
    
    # Price stability factor (0-1 point)
    'price_stability': {
        'max_change_percent': 20,  # Less than 20% change
        'points': 1
    }
}
