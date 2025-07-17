#!/usr/bin/env python3
"""
Test if using include parameter fixes missing token data in API responses
"""
import asyncio
import aiohttp
import json

async def test_include_parameter():
    """Test API with include parameter to get token data"""
    base_url = "https://api.geckoterminal.com/api/v2"
    headers = {
        'Accept': 'application/json;version=20230302'
    }
    
    async with aiohttp.ClientSession() as session:
        url = f"{base_url}/networks/base/new_pools?include=base_token,quote_token"
        print(f"🔍 Testing with include parameter: {url}")
        
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                pools = data.get('data', [])
                included = data.get('included', [])
                print(f"✅ Success: {len(pools)} pools, {len(included)} included items")
                
                if pools and included:
                    sample_pool = pools[0]
                    pool_attrs = sample_pool.get('attributes', {})
                    relationships = sample_pool.get('relationships', {})
                    
                    print(f"\n📋 Pool attributes:")
                    print(f"  - Liquidity: ${pool_attrs.get('reserve_in_usd', 'N/A')}")
                    print(f"  - Symbol: {pool_attrs.get('base_token_symbol', 'N/A')}")
                    print(f"  - Network: {pool_attrs.get('network', 'N/A')}")
                    print(f"  - Market Cap: ${pool_attrs.get('market_cap_usd', 'N/A')}")
                    
                    base_token_rel = relationships.get('base_token', {})
                    base_token_id = base_token_rel.get('data', {}).get('id')
                    print(f"  - Base token ID: {base_token_id}")
                    
                    print(f"\n📋 Looking for token data in included section:")
                    for item in included:
                        if item.get('type') == 'token' and item.get('id') == base_token_id:
                            token_attrs = item.get('attributes', {})
                            print(f"  ✅ Found matching token:")
                            print(f"    - Symbol: {token_attrs.get('symbol', 'N/A')}")
                            print(f"    - Name: {token_attrs.get('name', 'N/A')}")
                            print(f"    - Market Cap: ${token_attrs.get('market_cap_usd', 'N/A')}")
                            print(f"    - FDV: ${token_attrs.get('fdv_usd', 'N/A')}")
                            break
                    else:
                        print(f"  ❌ No matching token found in included section")
                        
                    token_count = sum(1 for item in included if item.get('type') == 'token')
                    print(f"\n📋 Total tokens in included: {token_count}")
                    
                    print(f"\n🔍 Testing filtering with real data:")
                    
                    liq_ranges = {
                        '10K-50K': 0,
                        '50K-250K': 0, 
                        '250K-1M': 0,
                        '1M+': 0
                    }
                    
                    for pool in pools:
                        try:
                            liquidity = float(pool.get('attributes', {}).get('reserve_in_usd', 0))
                            if 10000 <= liquidity <= 50000:
                                liq_ranges['10K-50K'] += 1
                            elif 50000 <= liquidity <= 250000:
                                liq_ranges['50K-250K'] += 1
                            elif 250000 <= liquidity <= 1000000:
                                liq_ranges['250K-1M'] += 1
                            elif liquidity >= 1000000:
                                liq_ranges['1M+'] += 1
                        except (ValueError, TypeError):
                            pass
                    
                    print(f"  Liquidity distribution:")
                    for range_name, count in liq_ranges.items():
                        print(f"    - {range_name}: {count} pools")
                        
            else:
                print(f"❌ Failed: HTTP {response.status}")
                
        print(f"\n🔍 Testing regular pools endpoint with include:")
        url2 = f"{base_url}/networks/base/pools?include=base_token,quote_token&limit=10"
        
        async with session.get(url2, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                pools = data.get('data', [])
                included = data.get('included', [])
                print(f"✅ Regular pools: {len(pools)} pools, {len(included)} included items")
                
                if pools and included:
                    sample_pool = pools[0]
                    pool_attrs = sample_pool.get('attributes', {})
                    print(f"  Sample pool liquidity: ${pool_attrs.get('reserve_in_usd', 'N/A')}")
                    print(f"  Sample pool market cap: ${pool_attrs.get('market_cap_usd', 'N/A')}")
                    
            else:
                print(f"❌ Regular pools failed: HTTP {response.status}")

if __name__ == "__main__":
    asyncio.run(test_include_parameter())
