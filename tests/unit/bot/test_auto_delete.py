#!/usr/bin/env python3
"""
Test auto-delete functionality for moonshot and rug alert button responses
"""
import sys
import os
import asyncio
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

async def test_auto_delete_alerts():
    """Test that moonshot and rug alert button responses schedule auto-delete"""
    try:
        from src.bot.button_handler import ButtonHandler
        from src.database.session_manager import SessionManager
        from unittest.mock import AsyncMock, MagicMock
        
        print("✅ Testing auto-delete functionality for alert button responses...")
        
        session_manager = SessionManager()
        test_chat_id = 12345
        
        session = session_manager.create_session(
            chat_id=test_chat_id,
            user_id=0,
            token_name="TEST",
            contract="0x1234567890abcdef",
            network="base",
            token_data={}
        )
        
        alert_context = {
            'type': 'moonshot',
            'contract': '0x1234567890abcdef',
            'network': 'base',
            'symbol': 'TEST'
        }
        session.alert_context = alert_context
        
        print(f"  Created test session with alert context")
        
        mock_api_client = AsyncMock()
        mock_reasoning_engine = MagicMock()
        mock_bot_handler = MagicMock()
        
        button_handler = ButtonHandler(
            api_client=mock_api_client,
            session_manager=session_manager,
            reasoning_engine=mock_reasoning_engine,
            bot_handler=mock_bot_handler
        )
        
        mock_query = MagicMock()
        mock_query.message.chat_id = test_chat_id
        mock_query.message.message_id = 999
        mock_query.edit_message_text = AsyncMock()
        
        deletion_calls = []
        
        async def mock_schedule_deletion(chat_id, message_id, deletion_time):
            deletion_calls.append({
                'chat_id': chat_id,
                'message_id': message_id,
                'deletion_time': deletion_time
            })
            print(f"    📅 Scheduled deletion for message {message_id} in {deletion_time} seconds")
        
        button_handler._schedule_message_deletion = mock_schedule_deletion
        
        print(f"\n  🔍 Testing alert analyze button...")
        mock_token_data = MagicMock()
        mock_token_data.name = "Test Token"
        mock_token_data.symbol = "TEST"
        mock_token_data.price_usd = 0.001
        mock_token_data.market_cap_usd = 1000000
        mock_token_data.volume_24h = 50000
        mock_token_data.liquidity = 25000
        mock_api_client.get_token_info.return_value = mock_token_data
        
        await button_handler.handle_alert_analyze_button(mock_query, "alert_analyze_base_0x1234567890abcdef")
        
        if deletion_calls and deletion_calls[-1]['deletion_time'] == 25 * 60:
            print(f"    ✅ Alert analyze button schedules 25-minute auto-delete")
        else:
            print(f"    ❌ Alert analyze button missing auto-delete")
            return False
        
        print(f"\n  🔍 Testing alert socials button...")
        mock_social_data = MagicMock()
        mock_social_data.twitter = "@test"
        mock_social_data.telegram = "@testchat"
        mock_social_data.website = "https://test.com"
        mock_social_data.coingecko_coin_id = "test-coin"
        mock_api_client.get_social_data.return_value = mock_social_data
        
        await button_handler.handle_alert_socials_button(mock_query, "alert_socials_base_0x1234567890abcdef")
        
        if len(deletion_calls) >= 2 and deletion_calls[-1]['deletion_time'] == 25 * 60:
            print(f"    ✅ Alert socials button schedules 25-minute auto-delete")
        else:
            print(f"    ❌ Alert socials button missing auto-delete")
            return False
        
        print(f"\n  🔍 Testing alert whale button...")
        await button_handler.handle_alert_whale_button(mock_query, "alert_whale_base_0x1234567890abcdef")
        
        if len(deletion_calls) >= 3 and deletion_calls[-1]['deletion_time'] == 25 * 60:
            print(f"    ✅ Alert whale button schedules 25-minute auto-delete")
        else:
            print(f"    ❌ Alert whale button missing auto-delete")
            return False
        
        print(f"\n  🔍 Testing alert BALZ button...")
        mock_reasoning_engine.classify_token.return_value = {
            'classification': 'POTENTIAL MOONSHOT',
            'confidence': 0.85,
            'reasoning': 'Test reasoning'
        }
        
        await button_handler.handle_alert_balz_button(mock_query, "alert_balz_base_0x1234567890abcdef")
        
        if len(deletion_calls) >= 4 and deletion_calls[-1]['deletion_time'] == 25 * 60:
            print(f"    ✅ Alert BALZ button schedules 25-minute auto-delete")
        else:
            print(f"    ❌ Alert BALZ button missing auto-delete")
            return False
        
        print(f"\n  🔍 Testing back to alert button...")
        await button_handler.handle_back_to_alert_button(mock_query, "back_to_alert_base_0x1234567890abcdef")
        
        if len(deletion_calls) >= 5 and deletion_calls[-1]['deletion_time'] == 25 * 60:
            print(f"    ✅ Back to alert button schedules 25-minute auto-delete")
        else:
            print(f"    ❌ Back to alert button missing auto-delete")
            return False
        
        print(f"\n  📊 Summary of deletion scheduling:")
        for i, call in enumerate(deletion_calls):
            print(f"    {i+1}. Message {call['message_id']} scheduled for deletion in {call['deletion_time']} seconds")
        
        print(f"\n🎉 Auto-delete test completed successfully!")
        print(f"  - All 5 alert button handlers schedule 25-minute auto-delete: ✅")
        print(f"  - Deletion time is consistent (1500 seconds): ✅")
        print(f"  - Alert context handling works: ✅")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_auto_delete_alerts())
    sys.exit(0 if success else 1)
