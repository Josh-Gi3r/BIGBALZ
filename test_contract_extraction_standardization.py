#!/usr/bin/env python3
"""
Test contract extraction standardization across all alert types
"""
import sys
import os
import asyncio
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

async def test_contract_extraction_standardization():
    """Test that all alert types use consistent contract extraction patterns"""
    try:
        from src.bot.button_handler import ButtonHandler
        from src.database.session_manager import SessionManager
        from unittest.mock import AsyncMock, MagicMock
        
        print("✅ Testing contract extraction standardization across all alert types...")
        
        session_manager = SessionManager()
        test_chat_id = 12345
        test_user_id = 67890
        test_contract = "0x1234567890abcdef"
        test_network = "base"
        test_symbol = "TEST"
        
        mock_api_client = AsyncMock()
        mock_reasoning_engine = MagicMock()
        mock_bot_handler = MagicMock()
        
        button_handler = ButtonHandler(
            api_client=mock_api_client,
            session_manager=session_manager,
            reasoning_engine=mock_reasoning_engine,
            bot_handler=mock_bot_handler
        )
        
        def mock_format_balz_response(classification, token_symbol):
            return f"BALZ RANK: {classification.category.value} for {token_symbol}"
        
        button_handler._format_balz_response = mock_format_balz_response
        
        mock_token_data = MagicMock()
        mock_token_data.name = "Test Token"
        mock_token_data.symbol = test_symbol
        mock_token_data.price_usd = 0.001
        mock_token_data.market_cap_usd = 1000000
        mock_token_data.fdv_usd = 1200000
        mock_token_data.volume_24h = 50000
        mock_token_data.liquidity = 25000
        mock_token_data.price_change_24h = 15.5
        mock_token_data.transactions_24h = 150
        mock_api_client.get_token_info.return_value = mock_token_data
        
        mock_social_data = MagicMock()
        mock_social_data.twitter = "@test"
        mock_api_client.get_social_info.return_value = mock_social_data
        
        mock_classification = MagicMock()
        mock_classification.category.value = "POTENTIAL MOONSHOT"
        mock_classification.confidence = 0.85
        mock_classification.reasoning = "Test reasoning"
        mock_reasoning_engine.classify_token.return_value = mock_classification
        
        api_calls = []
        
        def track_api_calls(method_name):
            async def wrapper(*args, **kwargs):
                api_calls.append({
                    'method': method_name,
                    'args': args,
                    'kwargs': kwargs
                })
                if method_name == 'get_token_info':
                    return mock_token_data
                elif method_name == 'get_social_info':
                    return mock_social_data
                return None
            return wrapper
        
        mock_api_client.get_token_info = track_api_calls('get_token_info')
        mock_api_client.get_social_info = track_api_calls('get_social_info')
        
        deletion_calls = []
        
        async def mock_schedule_deletion(chat_id, message_id, deletion_time):
            deletion_calls.append({
                'chat_id': chat_id,
                'message_id': message_id,
                'deletion_time': deletion_time
            })
        
        button_handler._schedule_message_deletion = mock_schedule_deletion
        
        print(f"\n  🔍 Testing Alert Button Handlers...")
        
        alert_session = session_manager.create_session(
            chat_id=test_chat_id,
            user_id=0,
            token_name=test_symbol,
            contract=test_contract,
            network=test_network,
            token_data={}
        )
        alert_context = {
            'type': 'moonshot',
            'contract': test_contract,
            'network': test_network,
            'symbol': test_symbol
        }
        alert_session.alert_context = alert_context
        
        mock_query = MagicMock()
        mock_query.message.chat_id = test_chat_id
        mock_query.message.message_id = 999
        mock_query.edit_message_text = AsyncMock()
        
        await button_handler.handle_alert_analyze_button(mock_query, f"alert_analyze_{test_network}_{test_contract}")
        
        updated_session = session_manager.get_session(test_chat_id, 0)
        if (hasattr(updated_session, 'current_contract') and 
            hasattr(updated_session, 'current_network') and
            updated_session.current_contract == test_contract and
            updated_session.current_network == test_network):
            print(f"    ✅ Alert analyze button uses session-based contract extraction")
        else:
            print(f"    ❌ Alert analyze button missing session properties")
            return False
        
        await button_handler.handle_alert_socials_button(mock_query, f"alert_socials_{test_network}_{test_contract}")
        
        await button_handler.handle_alert_balz_button(mock_query, f"alert_balz_{test_network}_{test_contract}")
        
        print(f"\n  🔍 Testing Gem Research Handlers...")
        
        await button_handler._handle_gem_analyze(mock_query, f"gem_analyze_{test_network}_{test_contract}")
        
        gem_session = session_manager.get_session(test_chat_id, test_user_id)
        if (gem_session and hasattr(gem_session, 'current_contract') and 
            hasattr(gem_session, 'current_network') and
            gem_session.current_contract == test_contract and
            gem_session.current_network == test_network):
            print(f"    ✅ Gem analyze handler uses session-based contract extraction")
        else:
            print(f"    ❌ Gem analyze handler missing session properties")
            return False
        
        await button_handler._handle_gem_socials(mock_query, f"gem_socials_{test_network}_{test_contract}")
        
        await button_handler._handle_gem_balz(mock_query, f"gem_balz_{test_network}_{test_contract}")
        
        print(f"\n  🔍 Testing API Method Consistency...")
        
        social_api_calls = [call for call in api_calls if call['method'] == 'get_social_info']
        if len(social_api_calls) >= 2:
            print(f"    ✅ All handlers use consistent 'get_social_info' method")
        else:
            print(f"    ❌ Inconsistent social API method usage")
            return False
        
        for call in api_calls:
            if call['method'] == 'get_token_info':
                args = call['args']
                if len(args) >= 2 and args[0] == test_network and args[1] == test_contract:
                    print(f"    ✅ API call uses correct network/contract parameters")
                else:
                    print(f"    ❌ API call has incorrect parameters: {args}")
                    return False
        
        print(f"\n  🔍 Testing Auto-Delete Consistency...")
        
        if len(deletion_calls) >= 5:
            all_25_minutes = all(call['deletion_time'] == 25 * 60 for call in deletion_calls)
            if all_25_minutes:
                print(f"    ✅ All handlers schedule 25-minute auto-delete")
            else:
                print(f"    ❌ Inconsistent auto-delete timing")
                return False
        else:
            print(f"    ❌ Missing auto-delete scheduling in some handlers")
            return False
        
        print(f"\n  📊 Summary of standardization:")
        print(f"    - Alert handlers: ✅ Session-based contract extraction")
        print(f"    - Gem handlers: ✅ Session-based contract extraction")
        print(f"    - API methods: ✅ Consistent naming (get_social_info)")
        print(f"    - Auto-delete: ✅ 25-minute scheduling across all handlers")
        print(f"    - Session management: ✅ Consistent properties stored")
        
        print(f"\n🎉 Contract extraction standardization test completed successfully!")
        print(f"  - All alert types use session-based contract extraction: ✅")
        print(f"  - API method naming is consistent: ✅")
        print(f"  - Auto-delete functionality is standardized: ✅")
        print(f"  - Session management is consistent: ✅")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_contract_extraction_standardization())
    sys.exit(0 if success else 1)
