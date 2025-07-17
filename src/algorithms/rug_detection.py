"""
Rug Detection Criteria - Proprietary Algorithm
Contains secret sauce thresholds for rug pull detection
"""

RUG_LIQUIDITY_DRAIN_CRITERIA = {
    'min_liquidity_drop_percent': 40,
    'min_initial_liquidity': 10000,
    'max_final_liquidity': 1000,
    'rug_type': 'LIQUIDITY_DRAIN'
}

RUG_PRICE_CRASH_CRITERIA = {
    'min_price_drop_percent': 60,
    'rug_type': 'PRICE_CRASH'
}

RUG_VOLUME_DUMP_CRITERIA = {
    'min_volume_spike_percent': 500,
    'min_price_drop_percent': 50,
    'min_previous_volume': 1000,
    'rug_type': 'VOLUME_DUMP'
}

RUG_CRITERIA_LIST = [
    RUG_LIQUIDITY_DRAIN_CRITERIA,
    RUG_PRICE_CRASH_CRITERIA,
    RUG_VOLUME_DUMP_CRITERIA
]

MAX_HISTORICAL_DATA_AGE = 120
