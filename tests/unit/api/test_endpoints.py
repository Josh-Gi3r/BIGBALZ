#!/usr/bin/env python3
"""
Test different API endpoints to find the correct new pools endpoint
"""
import sys
import os
import asyncio
import aiohttp

sys.path.insert(0, os.path.dirname(__file__))

async def test_api_endpoints():
    """Test different API endpoints to find working ones"""
    base_url = "https://api.geckoterminal.com/api/v2"
    headers = {
        'Accept': 'application/json;version=20230302'
    }
    
    endpoints_to_test = [
        "/networks/new_pools",
        "/networks/solana/new_pools", 
        "/networks/base/new_pools",
        "/networks/ethereum/new_pools",
        "/networks/trending_pools",
        "/networks/solana/pools?sort=h24_volume_usd_desc&limit=10",
        "/networks/base/pools?sort=h24_volume_usd_desc&limit=10"
    ]
    
    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints_to_test:
            try:
                url = f"{base_url}{endpoint}"
                print(f"\n🔍 Testing: {url}")
                
                async with session.get(url, headers=headers) as response:
                    print(f"Status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        pools = data.get('data', [])
                        print(f"✅ Success: {len(pools)} pools returned")
                        
                        if pools:
                            sample = pools[0]
                            attrs = sample.get('attributes', {})
                            print(f"  Sample pool:")
                            print(f"    - Symbol: {attrs.get('base_token_symbol', 'N/A')}")
                            print(f"    - Network: {attrs.get('network', 'N/A')}")
                            print(f"    - Liquidity: ${attrs.get('reserve_in_usd', 'N/A')}")
                            print(f"    - Market Cap: ${attrs.get('market_cap_usd', 'N/A')}")
                            
                            relationships = sample.get('relationships', {})
                            if relationships:
                                print(f"    - Has relationships: {list(relationships.keys())}")
                                base_token = relationships.get('base_token', {})
                                if base_token:
                                    token_data = base_token.get('data', {})
                                    print(f"    - Token ID: {token_data.get('id', 'N/A')}")
                    else:
                        print(f"❌ Failed: HTTP {response.status}")
                        
            except Exception as e:
                print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_api_endpoints())
