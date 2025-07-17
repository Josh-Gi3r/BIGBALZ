#!/usr/bin/env python3
"""
Test moonshot counter logic for 45-minute reports
"""
import sys
import os
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

def test_moonshot_counter():
    """Test moonshot counting logic"""
    try:
        from src.monitoring.background_monitor import MoonshotAlert, BackgroundMonitor
        
        print("✅ Testing moonshot counter logic...")
        
        now = datetime.utcnow()
        
        recent_moonshots = [
            MoonshotAlert(
                token_symbol="RECENT1",
                contract="0x1111111111111111",
                network="base",
                tier="POTENTIAL 100X",
                price_change_percent=75.0,
                volume_24h=15000,
                liquidity=25000,
                transaction_count=75,
                timestamp=now - timedelta(minutes=10)
            ),
            MoonshotAlert(
                token_symbol="RECENT2", 
                contract="0x2222222222222222",
                network="solana",
                tier="POTENTIAL 10X",
                price_change_percent=45.0,
                volume_24h=30000,
                liquidity=50000,
                transaction_count=100,
                timestamp=now - timedelta(minutes=30)
            ),
            MoonshotAlert(
                token_symbol="RECENT3",
                contract="0x3333333333333333", 
                network="eth",
                tier="POTENTIAL 2X",
                price_change_percent=25.0,
                volume_24h=75000,
                liquidity=100000,
                transaction_count=150,
                timestamp=now - timedelta(minutes=40)
            )
        ]
        
        old_moonshots = [
            MoonshotAlert(
                token_symbol="OLD1",
                contract="0x4444444444444444",
                network="base", 
                tier="POTENTIAL 100X",
                price_change_percent=80.0,
                volume_24h=20000,
                liquidity=30000,
                transaction_count=80,
                timestamp=now - timedelta(minutes=60)
            ),
            MoonshotAlert(
                token_symbol="OLD2",
                contract="0x5555555555555555",
                network="bsc",
                tier="POTENTIAL 10X", 
                price_change_percent=50.0,
                volume_24h=40000,
                liquidity=60000,
                transaction_count=120,
                timestamp=now - timedelta(hours=2)
            )
        ]
        
        monitor = BackgroundMonitor(None, None, None)
        
        all_moonshots = recent_moonshots + old_moonshots
        for moonshot in all_moonshots:
            monitor.detected_moonshots[moonshot.contract] = moonshot
            print(f"  Added moonshot: {moonshot.token_symbol} ({moonshot.tier}) at {moonshot.timestamp}")
        
        print(f"\n  Total moonshots in dict: {len(monitor.detected_moonshots)}")
        
        print(f"\n  🔍 Testing 45-minute counting...")
        counts = monitor._count_recent_moonshots_by_tier(45)
        
        print(f"  Counts returned: {counts}")
        
        expected_counts = {
            'POTENTIAL 100X': 1,  # RECENT1
            'POTENTIAL 10X': 1,   # RECENT2  
            'POTENTIAL 2X': 1     # RECENT3
        }
        
        print(f"  Expected counts: {expected_counts}")
        
        success = True
        for tier, expected_count in expected_counts.items():
            actual_count = counts.get(tier, 0)
            if actual_count == expected_count:
                print(f"    ✅ {tier}: {actual_count} (correct)")
            else:
                print(f"    ❌ {tier}: {actual_count} (expected {expected_count})")
                success = False
        
        print(f"\n  🔍 Testing different time windows...")
        
        counts_30 = monitor._count_recent_moonshots_by_tier(30)
        print(f"  30-minute counts: {counts_30}")
        
        counts_120 = monitor._count_recent_moonshots_by_tier(120)
        print(f"  120-minute counts: {counts_120}")
        
        if success:
            print(f"\n🎉 Moonshot counter test completed successfully!")
        else:
            print(f"\n❌ Moonshot counter test failed!")
            
        return success
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_moonshot_counter()
    sys.exit(0 if success else 1)
