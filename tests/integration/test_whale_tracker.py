#!/usr/bin/env python3
"""
Test whale tracker functionality to determine if it actually works
"""
import sys
import os
import asyncio
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

async def test_whale_tracker_functionality():
    """Test whale tracker implementation to identify issues"""
    try:
        from src.api.geckoterminal_client import GeckoTerminalClient
        from src.bot.button_handler import ButtonHandler
        from src.database.session_manager import SessionManager
        from unittest.mock import AsyncMock, MagicMock
        
        print("🐋 Testing whale tracker functionality...")
        
        print("\n  🔍 Testing whale tracker API method...")
        
        api_client = GeckoTerminalClient()
        
        test_network = "base"
        test_pool_address = "0x1234567890abcdef1234567890abcdef12345678"  # Mock pool address
        
        print(f"    API method exists: {hasattr(api_client, 'get_whale_trades')}")
        print(f"    Method signature: {api_client.get_whale_trades.__doc__}")
        
        print("\n  🔍 Testing button handler whale tracker integration...")
        
        session_manager = SessionManager()
        mock_bot_handler = MagicMock()
        
        button_handler = ButtonHandler(
            api_client=api_client,
            session_manager=session_manager,
            reasoning_engine=None,
            bot_handler=mock_bot_handler
        )
        
        print(f"    ButtonHandler has whale_tracker attribute: {hasattr(button_handler, 'whale_tracker')}")
        print(f"    whale_tracker value: {getattr(button_handler, 'whale_tracker', 'NOT_SET')}")
        
        print("\n  🔍 Checking for whale tracker class...")
        
        try:
            from src.analysis.whale_tracker import WhaleTracker
            print("    ✅ WhaleTracker class found")
            whale_tracker = WhaleTracker(api_client)
            print(f"    WhaleTracker methods: {[method for method in dir(whale_tracker) if not method.startswith('_')]}")
        except ImportError as e:
            print(f"    ❌ WhaleTracker class not found: {e}")
        except Exception as e:
            print(f"    ❌ Error importing WhaleTracker: {e}")
        
        print("\n  🔍 Testing gem research whale handler...")
        
        test_chat_id = 12345
        test_user_id = 67890
        test_contract = "0xabcdef1234567890abcdef1234567890abcdef12"
        test_network = "base"
        
        session = session_manager.create_session(
            chat_id=test_chat_id,
            user_id=test_user_id,
            token_name="TEST",
            contract=test_contract,
            network=test_network,
            token_data={}
        )
        
        mock_query = MagicMock()
        mock_query.message.chat_id = test_chat_id
        mock_query.message.message_id = 999
        mock_query.edit_message_text = AsyncMock()
        
        try:
            await button_handler._handle_gem_whale(mock_query, f"gem_whale_{test_network}_{test_contract}")
            print("    ✅ Gem whale handler executed without errors")
        except Exception as e:
            print(f"    ❌ Gem whale handler failed: {e}")
        
        print("\n  🔍 Testing alert whale handler...")
        
        alert_session = session_manager.create_session(
            chat_id=test_chat_id,
            user_id=0,
            token_name="TEST",
            contract=test_contract,
            network=test_network,
            token_data={}
        )
        alert_context = {
            'type': 'moonshot',
            'contract': test_contract,
            'network': test_network,
            'symbol': 'TEST'
        }
        alert_session.alert_context = alert_context
        
        try:
            await button_handler.handle_alert_whale_button(mock_query, f"alert_whale_{test_network}_{test_contract}")
            print("    ✅ Alert whale handler executed without errors")
        except Exception as e:
            print(f"    ❌ Alert whale handler failed: {e}")
        
        print("\n  🔍 Testing pool address resolution...")
        
        try:
            token_data = await api_client.get_token_info(test_network, test_contract)
            if token_data:
                print("    ✅ Token data retrieved successfully")
                print(f"    Token has pool info: {hasattr(token_data, 'pool_address') or 'pool_address' in str(token_data)}")
            else:
                print("    ❌ Could not retrieve token data")
        except Exception as e:
            print(f"    ❌ Error getting token data: {e}")
        
        print("\n  🔍 Testing whale trades API call...")
        
        try:
            whale_trades = await api_client.get_whale_trades(test_network, test_pool_address, limit=5)
            if whale_trades is not None:
                print(f"    ✅ Whale trades API call successful, returned {len(whale_trades)} trades")
                if whale_trades:
                    print(f"    Sample trade structure: {list(whale_trades[0].keys()) if whale_trades else 'No trades'}")
            else:
                print("    ❌ Whale trades API call returned None")
        except Exception as e:
            print(f"    ❌ Whale trades API call failed: {e}")
        
        print("\n📊 WHALE TRACKER ANALYSIS SUMMARY:")
        print("=" * 50)
        
        issues_found = []
        
        if not hasattr(button_handler, 'whale_tracker') or button_handler.whale_tracker is None:
            issues_found.append("❌ ButtonHandler.whale_tracker is None - whale tracker not initialized")
        
        try:
            from src.analysis.whale_tracker import WhaleTracker
        except ImportError:
            issues_found.append("❌ WhaleTracker class does not exist")
        
        if issues_found:
            print("🔴 CRITICAL ISSUES FOUND:")
            for issue in issues_found:
                print(f"  {issue}")
        else:
            print("🟡 WHALE TRACKER PARTIALLY IMPLEMENTED:")
            print("  ✅ API method exists")
            print("  ✅ Button handlers exist")
            print("  ⚠️ Need to verify actual functionality with real data")
        
        print("\n🔧 RECOMMENDATIONS:")
        if not hasattr(button_handler, 'whale_tracker') or button_handler.whale_tracker is None:
            print("  1. Create WhaleTracker class in src/analysis/whale_tracker.py")
            print("  2. Initialize whale_tracker in ButtonHandler.__init__")
            print("  3. Implement pool address resolution from token contracts")
            print("  4. Add whale trade analysis and formatting logic")
        else:
            print("  1. Test with real pool addresses and API calls")
            print("  2. Verify whale trade data parsing and formatting")
            print("  3. Check rate limiting and error handling")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_whale_tracker_functionality())
    sys.exit(0 if success else 1)
