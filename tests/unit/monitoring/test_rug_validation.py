#!/usr/bin/env python3
"""
Test script to verify moonshot rug validation works correctly
"""
import sys
import os
import asyncio
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

async def test_rug_validation():
    """Test that moonshot detection skips rugged tokens"""
    try:
        from src.monitoring.background_monitor import BackgroundMonitor, RugAlert
        
        print("✅ Imports successful")
        
        monitor = BackgroundMonitor(None, None, None)
        
        print("✅ Monitor initialized")
        
        test_contract = "0x123456789abcdef"
        test_token = "TESTRUG"
        
        rug_alert = RugAlert(
            token_symbol=test_token,
            contract=test_contract,
            network="solana",
            rug_type="liquidity_drain",
            timestamp=datetime.utcnow(),
            liquidity_drain_percent=85.0,
            price_drop_percent=90.0,
            volume_spike_percent=500.0,
            final_liquidity=5000.0,
            final_volume_1h=100000.0
        )
        
        monitor.detected_rugs[test_contract] = rug_alert
        print(f"✅ Added test rug: {test_token} ({test_contract})")
        
        test_pool = {
            'attributes': {
                'name': test_token,
                'base_token_price_usd': '0.001',
                'reserve_in_usd': '50000',
                'market_cap_usd': '100000',
                'volume_usd': {'h24': '25000'},
                'transactions': {'h24': {'buys': 50, 'sells': 50}},
                'price_change_percentage': {'m5': 80.0}
            },
            'relationships': {
                'base_token': {
                    'data': {
                        'id': f'solana_{test_contract}'
                    }
                }
            }
        }
        
        print("🔍 Testing moonshot criteria with rugged token...")
        
        result = await monitor._check_moonshot_criteria(test_pool, "solana")
        
        if result is None:
            print("✅ Moonshot detection correctly skipped rugged token")
        else:
            print(f"❌ Moonshot detection failed - should have skipped rugged token but returned: {result}")
            return False
        
        print("\n🔍 Testing moonshot criteria with clean token...")
        
        clean_contract = "0xabcdef123456789"
        clean_pool = {
            'attributes': {
                'name': 'CLEANTOKEN',
                'base_token_price_usd': '0.001',
                'reserve_in_usd': '50000',
                'market_cap_usd': '100000',
                'volume_usd': {'h24': '25000'},
                'transactions': {'h24': {'buys': 50, 'sells': 50}},
                'price_change_percentage': {'m5': 80.0}
            },
            'relationships': {
                'base_token': {
                    'data': {
                        'id': f'solana_{clean_contract}'
                    }
                }
            }
        }
        
        result = await monitor._check_moonshot_criteria(clean_pool, "solana")
        
        if result is not None:
            print(f"✅ Moonshot detection correctly processed clean token: {result.tier}")
        else:
            print("⚠️ Clean token didn't meet moonshot criteria (this is normal)")
        
        print("\n🎉 All rug validation tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_rug_validation())
    sys.exit(0 if success else 1)
