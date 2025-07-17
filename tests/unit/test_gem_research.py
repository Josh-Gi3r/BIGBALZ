#!/usr/bin/env python3
"""
Test script to debug gem research API calls and filtering
"""
import sys
import os
import asyncio
import json

sys.path.insert(0, os.path.dirname(__file__))

async def test_gem_research_api():
    """Test the complete gem research API flow"""
    try:
        from src.api.geckoterminal_client import GeckoTerminalClient
        from src.bot.gem_research_handler import GemResearchHandler
        
        print("✅ Imports successful")
        
        api_client = GeckoTerminalClient()
        gem_handler = GemResearchHandler(api_client, None, None)
        
        print("✅ Handlers initialized")
        
        print("\n🔍 Testing new pools API call...")
        try:
            new_pools = await api_client.get_new_pools_paginated(max_pages=2)
            print(f"✅ Fetched {len(new_pools)} new pools")
            
            if new_pools:
                sample_pool = new_pools[0]
                print(f"Sample pool structure:")
                print(f"  - Pool ID: {sample_pool.get('id', 'N/A')}")
                print(f"  - Attributes keys: {list(sample_pool.get('attributes', {}).keys())}")
                print(f"  - Network: {sample_pool.get('attributes', {}).get('network', 'N/A')}")
                print(f"  - Base token: {sample_pool.get('attributes', {}).get('base_token_symbol', 'N/A')}")
                print(f"  - Liquidity: ${sample_pool.get('attributes', {}).get('reserve_in_usd', 'N/A')}")
                print(f"  - Market cap: ${sample_pool.get('attributes', {}).get('market_cap_usd', 'N/A')}")
            else:
                print("❌ No pools returned from API")
                return False
                
        except Exception as e:
            print(f"❌ API call failed: {e}")
            return False
        
        print("\n🔍 Testing network filtering...")
        networks = ['solana', 'ethereum', 'bsc', 'base']
        for network in networks:
            network_pools = [p for p in new_pools if p.get('attributes', {}).get('network') == network]
            print(f"  - {network}: {len(network_pools)} pools")
        
        print("\n🔍 Testing complete gem research flow...")
        
        from src.bot.gem_research_handler import GemResearchSession
        test_session = GemResearchSession(
            chat_id=12345,
            user_id=67890,
            step='results',
            criteria={
                'network': 'solana',
                'age': 'last_48',
                'liquidity': '10_50',  # $10K-$50K
                'mcap': 'micro'  # Under $1M
            },
            new_pools_list=new_pools[:100],  # Use first 100 pools
            final_pools=[],
            current_index=0,
            timestamp=1234567890
        )
        
        print(f"Test session created with {len(test_session.new_pools_list)} pools")
        
        print("\n🔍 Testing pool filtering...")
        filtered_pools = gem_handler._filter_pools_by_criteria(test_session)
        print(f"After filtering: {len(filtered_pools)} pools match criteria")
        
        if filtered_pools:
            print("✅ Found matching pools!")
            for i, pool in enumerate(filtered_pools[:3]):  # Show first 3
                attrs = pool.get('attributes', {})
                print(f"  Pool {i+1}:")
                print(f"    - Symbol: {attrs.get('base_token_symbol', 'N/A')}")
                print(f"    - Network: {attrs.get('network', 'N/A')}")
                print(f"    - Liquidity: ${attrs.get('reserve_in_usd', 'N/A')}")
                print(f"    - Market Cap: ${attrs.get('market_cap_usd', 'N/A')}")
        else:
            print("❌ No pools match the test criteria")
            
            print("\n🔍 Debugging filter criteria...")
            
            network_matches = [p for p in test_session.new_pools_list 
                             if p.get('attributes', {}).get('network') == 'solana']
            print(f"  - Network 'solana' matches: {len(network_matches)}")
            
            liq_matches = []
            for pool in network_matches:
                try:
                    liquidity = float(pool.get('attributes', {}).get('reserve_in_usd', 0))
                    if 10000 <= liquidity <= 50000:
                        liq_matches.append(pool)
                except (ValueError, TypeError):
                    pass
            print(f"  - Liquidity $10K-$50K matches: {len(liq_matches)}")
            
            mcap_matches = []
            for pool in liq_matches:
                try:
                    mcap = float(pool.get('attributes', {}).get('market_cap_usd', 0))
                    if mcap < 1000000:  # Under $1M
                        mcap_matches.append(pool)
                except (ValueError, TypeError):
                    pass
            print(f"  - Market cap <$1M matches: {len(mcap_matches)}")
        
        print("\n🎉 API test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_gem_research_api())
    sys.exit(0 if success else 1)
