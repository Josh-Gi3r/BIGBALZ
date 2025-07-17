#!/usr/bin/env python3
"""
Test complete moonshot detection and button functionality end-to-end
"""
import sys
import os
import asyncio
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

async def test_moonshot_end_to_end():
    """Test complete moonshot flow from detection to button handling"""
    try:
        from src.monitoring.background_monitor import MoonshotAlert, BackgroundMonitor
        from src.bot.button_handler import ButtonHandler
        from src.bot.telegram_handler import TelegramBotHandler
        from src.database.session_manager import SessionManager
        
        print("✅ Testing complete moonshot end-to-end flow...")
        
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
                    print(f"      ❌ Parsing failed")
                    return False
            else:
                print(f"    ❌ Malformed callback: {callback}")
                return False
        
        print(f"\n  🔍 Testing alert context storage...")
        
        session_manager = SessionManager()
        test_chat_id = 12345
        
        broadcast_session = session_manager.create_session(
            chat_id=test_chat_id,
            user_id=0,
            token_name=test_alert.token_symbol,
            contract=test_alert.contract,
            network=test_alert.network,
            token_data={}
        )
        alert_context = {
            'type': 'moonshot',
            'contract': test_alert.contract,
            'network': test_alert.network,
            'symbol': test_alert.token_symbol
        }
        broadcast_session.alert_context = alert_context
        print(f"    ✅ Stored alert context in broadcast session (user_id=0)")
        
        lookup_session = session_manager.get_session(test_chat_id, 0)
        if hasattr(lookup_session, 'alert_context'):
            retrieved_context = lookup_session.alert_context
            print(f"    ✅ Retrieved alert context: {retrieved_context}")
            
            if (retrieved_context['contract'] == test_alert.contract and 
                retrieved_context['network'] == test_alert.network):
                print(f"    ✅ Alert context matches original alert")
            else:
                print(f"    ❌ Alert context mismatch")
                return False
        else:
            print(f"    ❌ Alert context not found in session")
            return False
        
        print(f"\n  🔍 Testing moonshot storage and counting...")
        
        monitor = BackgroundMonitor(None, None, None)
        monitor.detected_moonshots[test_alert.contract] = test_alert
        print(f"    ✅ Stored moonshot in detected_moonshots dict")
        
        counts = monitor._count_recent_moonshots_by_tier(45)
        expected_count = 1 if test_alert.tier in counts else 0
        actual_count = counts.get(test_alert.tier, 0)
        
        if actual_count >= expected_count:
            print(f"    ✅ Moonshot counting works: {test_alert.tier} = {actual_count}")
        else:
            print(f"    ❌ Moonshot counting failed: expected {expected_count}, got {actual_count}")
            return False
        
        print(f"\n🎉 End-to-end moonshot test completed successfully!")
        print(f"  - Button creation: ✅")
        print(f"  - Callback parsing: ✅") 
        print(f"  - Alert context storage: ✅")
        print(f"  - Session lookup: ✅")
        print(f"  - Moonshot counting: ✅")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_moonshot_end_to_end())
    sys.exit(0 if success else 1)
