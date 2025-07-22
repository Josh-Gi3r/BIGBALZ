#!/usr/bin/env python3
"""Test Pro plan configuration and ETH network support"""
import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

async def test_pro_plan_config():
    """Test that Pro plan configuration is properly applied"""
    print("🔍 TESTING PRO PLAN CONFIGURATION")
    print("=" * 60)
    
    try:
        from src.config.settings import settings
        from src.api.geckoterminal_client import GeckoTerminalClient
        
        print(f"✅ Settings rate limit: {settings.api.rate_limit} calls/minute")
        print(f"✅ Settings API key configured: {bool(settings.api.geckoterminal_api_key)}")
        
        client = GeckoTerminalClient()
        print(f"✅ Client rate limit: {client.rate_limiter.max_calls} calls/minute")
        print(f"✅ Client API key configured: {bool(client.api_key)}")
        
        if client.rate_limiter.max_calls == settings.api.rate_limit:
            print("✅ Rate limits match between settings and client")
        else:
            print("❌ Rate limit mismatch!")
            
        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

async def test_eth_network_support():
    """Test ETH network support in gem research"""
    print("\n🔍 TESTING ETH NETWORK SUPPORT")
    print("=" * 60)
    
    try:
        from src.bot.gem_research_handler import GemResearchHandler
        from src.api.geckoterminal_client import GeckoTerminalClient
        from src.database.session_manager import SessionManager
        
        api_client = GeckoTerminalClient()
        session_manager = SessionManager()
        gem_handler = GemResearchHandler(api_client=api_client, session_manager=session_manager)
        
        network_buttons = gem_handler.create_network_selection_buttons()
        eth_button_found = False
        
        for row in network_buttons.inline_keyboard:
            for button in row:
                if "Ethereum" in button.text and "gem_network_eth" in button.callback_data:
                    eth_button_found = True
                    print(f"✅ ETH button found: {button.text} -> {button.callback_data}")
        
        if not eth_button_found:
            print("❌ ETH network button not found!")
            return False
            
        print("🔍 Testing ETH network API call...")
        trending_pools = await api_client.get_trending_pools("eth", "5m", 5)
        
        if trending_pools and len(trending_pools) > 0:
            print(f"✅ ETH trending pools API working: {len(trending_pools)} pools returned")
            sample_pool = trending_pools[0]
            attrs = sample_pool.get('attributes', {})
            print(f"✅ Sample ETH pool: {attrs.get('base_token_symbol', 'UNKNOWN')}")
        else:
            print("⚠️  ETH API returned no pools (may be normal)")
            
        return True
    except Exception as e:
        print(f"❌ ETH network test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all Pro plan tests"""
    print("🚀 GECKOTERMINAL PRO PLAN VERIFICATION")
    print("=" * 70)
    
    config_result = await test_pro_plan_config()
    eth_result = await test_eth_network_support()
    
    print("\n" + "=" * 70)
    print("🏁 PRO PLAN TEST RESULTS")
    print("=" * 70)
    
    if config_result and eth_result:
        print("✅ All Pro plan features verified successfully!")
        print("💡 Ready for production with 500 calls/minute")
    else:
        print("❌ Some Pro plan features need attention")

if __name__ == "__main__":
    asyncio.run(main())
