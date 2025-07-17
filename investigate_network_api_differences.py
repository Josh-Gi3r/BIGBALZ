#!/usr/bin/env python3
"""Investigate why different networks have different API behaviors"""
import asyncio
import sys
import os
import time

sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

async def investigate_api_endpoints():
    from api.geckoterminal_client import GeckoTerminalClient
    
    api_client = GeckoTerminalClient()
    networks = ['solana', 'ethereum', 'bsc', 'base']
    
    print("🔍 INVESTIGATING NETWORK-SPECIFIC API BEHAVIORS\n")
    
    for network in networks:
        print(f"🌐 {network.upper()} Network Analysis:")
        
        try:
            print(f"  Testing new_pools endpoint... ", end="")
            start_time = time.time()
            new_pools = await api_client.get_new_pools_paginated(network, max_pools=5)
            end_time = time.time()
            print(f"✅ {len(new_pools)} pools ({end_time-start_time:.2f}s)")
            
            if len(new_pools) > 0:
                sample = new_pools[0].get('attributes', {})
                print(f"    Sample data quality:")
                print(f"      Liquidity: ${float(sample.get('reserve_in_usd', 0)):,.0f}")
                print(f"      Market Cap: ${float(sample.get('market_cap_usd', 0)):,.0f}")
                print(f"      FDV: ${float(sample.get('fdv_usd', 0)):,.0f}")
                
                liquidity_count = sum(1 for p in new_pools if float(p.get('attributes', {}).get('reserve_in_usd', 0)) > 0)
                mcap_count = sum(1 for p in new_pools if float(p.get('attributes', {}).get('market_cap_usd', 0)) > 0)
                fdv_count = sum(1 for p in new_pools if float(p.get('attributes', {}).get('fdv_usd', 0)) > 0)
                
                print(f"    Data completeness ({len(new_pools)} pools):")
                print(f"      With liquidity: {liquidity_count}/{len(new_pools)}")
                print(f"      With market cap: {mcap_count}/{len(new_pools)}")
                print(f"      With FDV: {fdv_count}/{len(new_pools)}")
            
            print(f"  Testing pools endpoint... ", end="")
            start_time = time.time()
            pools = await api_client.get_pools_paginated(network, max_pools=5)
            end_time = time.time()
            print(f"✅ {len(pools)} pools ({end_time-start_time:.2f}s)")
            
            if len(pools) > 0:
                sample = pools[0].get('attributes', {})
                print(f"    Sample pool:")
                print(f"      Symbol: {sample.get('base_token_symbol', 'N/A')}")
                print(f"      Volume 24h: ${float(sample.get('volume_usd', {}).get('h24', 0)):,.0f}")
                print(f"      Liquidity: ${float(sample.get('reserve_in_usd', 0)):,.0f}")
                
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            if "404" in str(e):
                print(f"    🔍 404 Error suggests endpoint doesn't exist for {network}")
            elif "rate limit" in str(e).lower():
                print(f"    🔍 Rate limiting issue for {network}")
            elif "token not found" in str(e).lower():
                print(f"    🔍 Network may not be supported or endpoint unavailable")
        
        print()
        await asyncio.sleep(3)

async def test_rate_limiting_behavior():
    from api.geckoterminal_client import GeckoTerminalClient
    
    print("🔍 TESTING RATE LIMITING BEHAVIOR ACROSS NETWORKS\n")
    
    api_client = GeckoTerminalClient()
    networks = ['solana', 'bsc', 'base']
    
    for network in networks:
        print(f"🌐 Testing {network.upper()} rate limiting:")
        
        try:
            start_time = time.time()
            
            for i in range(3):
                print(f"  Request {i+1}/3... ", end="")
                pools = await api_client.get_new_pools_paginated(network, max_pools=10)
                print(f"✅ {len(pools)} pools")
                
            end_time = time.time()
            print(f"  Total time for 3 requests: {end_time-start_time:.2f}s")
            
            rate_status = api_client.get_rate_limit_status()
            print(f"  Rate limit status: {rate_status['remaining_calls']}/{rate_status['max_calls_per_minute']} remaining")
            
        except Exception as e:
            print(f"  ❌ ERROR: {str(e)}")
        
        print()
        await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(investigate_api_endpoints())
    asyncio.run(test_rate_limiting_behavior())
