"""
Whale Confidence Scoring - Proprietary Algorithm
Contains secret sauce thresholds and scoring logic for whale analysis
"""

# Whale thresholds as percentage of total supply
WHALE_THRESHOLDS = {
    'mega_whale': 5.0,    # 5%+ of supply
    'large_whale': 2.0,   # 2-5% of supply
    'medium_whale': 1.0,  # 1-2% of supply
    'small_whale': 0.5    # 0.5-1% of supply
}

WHALE_VOLUME_THRESHOLD = 0.5  # 0.5% of total volume

CONFIDENCE_SCORING = {
    'base_score': 5.0,  # Start at neutral
    
    'whale_diversity': {
        'excellent': {'min_count': 10, 'score_bonus': 1.0},
        'good': {'min_count': 5, 'score_bonus': 0.5},
        'poor': {'max_count': 2, 'score_penalty': -1.0}
    },
    
    'holdings_distribution': {
        'healthy_range': {'min': 20, 'max': 40, 'score_bonus': 1.0},
        'good_distribution': {'max': 20, 'score_bonus': 0.5},
        'too_concentrated_severe': {'min': 60, 'score_penalty': -2.0},
        'too_concentrated_moderate': {'min': 50, 'score_penalty': -1.0}
    },
    
    'buy_sell_ratio': {
        'strong_buying': {'min_ratio': 2.0, 'score_bonus': 1.5},
        'moderate_buying': {'min_ratio': 1.5, 'score_bonus': 1.0},
        'slight_buying': {'min_ratio': 1.0, 'score_bonus': 0.5},
        'heavy_selling': {'max_ratio': 0.5, 'score_penalty': -1.5},
        'moderate_selling': {'max_ratio': 0.75, 'score_penalty': -1.0}
    },
    
    'recent_activity': {
        'buy_pressure_bonus': 1.0,
        'sell_pressure_penalty': -1.0
    },
    
    # Factor 5: Top whale concentration
    'top_whale_concentration': {
        'too_dominant_severe': {'min_percentage': 20, 'score_penalty': -1.5},
        'too_dominant_moderate': {'min_percentage': 15, 'score_penalty': -0.5}
    }
}

RISK_LEVELS = {
    'LOW': {'min_score': 7},
    'MEDIUM': {'min_score': 4},
    'HIGH': {'max_score': 4}
}

RECENT_ACTIVITY_TIMEFRAME = 24
