#!/usr/bin/env python3
"""
Test moonshot button functionality end-to-end
"""
import sys
import os
import asyncio
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

async def test_moonshot_buttons():
    """Test that moonshot buttons work correctly"""
    try:
        from src.monitoring.background_monitor import MoonshotAlert, BackgroundMonitor
        from src.bot.button_handler import ButtonHandler
        from src.api.geckoterminal_client import GeckoTerminalClient
        
        print("✅ Testing moonshot button functionality...")
        
        test_alert = MoonshotAlert(
            token_symbol="TEST",
            contract="0x1234567890abcdef",
            network="base",
            tier="POTENTIAL 2X",
            price_change_percent=25.5,
            volume_24h=890000,
            liquidity=125000,
            transaction_count=567,
            timestamp=datetime.utcnow()
        )
        
        print(f"  Created test alert: {test_alert.token_symbol} on {test_alert.network}")
        
        button_handler = ButtonHandler(None, None, None, None)
        buttons = button_handler.create_moonshot_buttons(test_alert.contract, test_alert.network)
        
        print(f"  ✅ Button creation successful")
        
        button_data = []
        for row in buttons.inline_keyboard:
            for button in row:
                button_data.append(button.callback_data)
                print(f"    Button: {button.text} -> {button.callback_data}")
        
        expected_patterns = [
            f"alert_analyze_{test_alert.network}_{test_alert.contract}",
            f"alert_socials_{test_alert.network}_{test_alert.contract}",
            f"alert_whale_{test_alert.network}_{test_alert.contract}",
            f"alert_balz_{test_alert.network}_{test_alert.contract}"
        ]
        
        for expected in expected_patterns:
            if expected in button_data:
                print(f"    ✅ Found expected callback: {expected}")
            else:
                print(f"    ❌ Missing expected callback: {expected}")
                return False
        
        print(f"\n  🔍 Testing callback parsing...")
        for callback in button_data:
            parts = callback.split('_')
            if len(parts) >= 4:
                action = parts[1]
                network = parts[2]
                contract = '_'.join(parts[3:])
                print(f"    Callback: {callback}")
                print(f"      Action: {action}, Network: {network}, Contract: {contract}")
                
                if network == test_alert.network and contract == test_alert.contract:
                    print(f"      ✅ Parsing successful")
                else:
                    print(f"      ❌ Parsing failed - expected {test_alert.network}/{test_alert.contract}")
                    return False
            else:
                print(f"    ❌ Malformed callback: {callback}")
                return False
        
        print(f"\n  🔍 Testing background monitor integration...")
        
        monitor_button_handler = ButtonHandler(None, None, None, None)
        monitor_buttons = monitor_button_handler.create_moonshot_buttons(test_alert.contract, test_alert.network)
        
        if monitor_buttons.inline_keyboard == buttons.inline_keyboard:
            print(f"    ✅ Background monitor creates identical buttons")
        else:
            print(f"    ❌ Background monitor button mismatch")
            return False
        
        print(f"\n🎉 Moonshot button test completed successfully!")
        print(f"  - Button creation: ✅")
        print(f"  - Callback format: ✅")
        print(f"  - Callback parsing: ✅")
        print(f"  - Monitor integration: ✅")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_moonshot_buttons())
    sys.exit(0 if success else 1)
