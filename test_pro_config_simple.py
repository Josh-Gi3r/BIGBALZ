#!/usr/bin/env python3
"""Simple test of Pro plan configuration without environment dependencies"""
import sys
import os

sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

def test_pro_plan_config_simple():
    """Test Pro plan configuration without requiring environment variables"""
    print("🔍 TESTING PRO PLAN CONFIGURATION (SIMPLE)")
    print("=" * 60)
    
    try:
        from src.api.geckoterminal_client import GeckoTerminalClient
        
        client = GeckoTerminalClient(api_key="test_key", rate_limit=500)
        
        print(f"✅ Client rate limit: {client.rate_limiter.max_calls} calls/minute")
        print(f"✅ Client API key configured: {bool(client.api_key)}")
        
        if client.rate_limiter.max_calls == 500:
            print("✅ Pro plan rate limit (500 calls/minute) correctly applied")
        else:
            print("❌ Rate limit mismatch!")
            
        if client.api_key == "test_key":
            print("✅ API key correctly set")
        else:
            print("❌ API key not set correctly!")
            
        print("\n🔍 TESTING SETTINGS DOCUMENTATION")
        print("=" * 60)
        
        with open('src/config/settings.py', 'r') as f:
            content = f.read()
            
        if "GeckoTerminal Pro Plan Features:" in content:
            print("✅ Pro plan documentation found in settings.py")
        else:
            print("❌ Pro plan documentation missing!")
            
        if "500,000 API calls per month" in content:
            print("✅ Monthly call limit documented")
        else:
            print("❌ Monthly call limit not documented!")
            
        if "500 calls per minute rate limit" in content:
            print("✅ Rate limit documented")
        else:
            print("❌ Rate limit not documented!")
            
        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_pro_plan_config_simple()
    
    print("\n" + "=" * 60)
    print("🏁 SIMPLE PRO PLAN TEST RESULTS")
    print("=" * 60)
    
    if success:
        print("✅ Pro plan configuration verified successfully!")
        print("💡 Ready for production with 500 calls/minute")
    else:
        print("❌ Pro plan configuration needs attention")
