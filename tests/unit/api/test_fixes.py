#!/usr/bin/env python3
"""
Test script to verify the fixed GeckoTerminal API client methods
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from api.geckoterminal_client import GeckoTerminalClient

async def test_api_methods():
    """Test the new paginated API methods"""
    client = GeckoTerminalClient()
    
    print("Testing GeckoTerminal API fixes...")
    
    print("\n1. Testing get_new_pools (global endpoint)...")
    try:
        new_pools = await client.get_new_pools('solana', limit=5)
        print(f"✅ Got {len(new_pools)} new pools")
        if new_pools:
            pool = new_pools[0]
            attrs = pool.get('attributes', {})
            print(f"   Sample pool: {attrs.get('base_token_symbol', 'N/A')} - {attrs.get('reserve_in_usd', 0)}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n2. Testing get_new_pools_paginated...")
    try:
        paginated_pools = await client.get_new_pools_paginated('solana', max_pools=50)
        print(f"✅ Got {len(paginated_pools)} pools via pagination")
        if paginated_pools:
            pool = paginated_pools[0]
            attrs = pool.get('attributes', {})
            print(f"   Sample pool: {attrs.get('base_token_symbol', 'N/A')} - Network: {attrs.get('network', 'N/A')}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n3. Testing get_pools_paginated...")
    try:
        pools = await client.get_pools_paginated('solana', max_pools=20)
        print(f"✅ Got {len(pools)} pools via pagination")
        if pools:
            pool = pools[0]
            attrs = pool.get('attributes', {})
            print(f"   Sample pool: {attrs.get('base_token_symbol', 'N/A')} - Volume: {attrs.get('volume_usd', {}).get('h24', 0)}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n4. Testing base_token_address extraction...")
    try:
        pools = await client.get_new_pools('solana', limit=2)
        if pools:
            for i, pool in enumerate(pools[:2]):
                print(f"   Pool {i+1} structure:")
                print(f"     Full pool keys: {list(pool.keys())}")
                attrs = pool.get('attributes', {})
                print(f"     Attributes keys: {list(attrs.keys())}")
                base_token_addr = attrs.get('base_token_address')
                symbol = attrs.get('base_token_symbol', 'N/A')
                print(f"     Symbol: {symbol}, Address: {base_token_addr}")
                
                relationships = pool.get('relationships', {})
                if relationships:
                    print(f"     Relationships keys: {list(relationships.keys())}")
                    base_token = relationships.get('base_token', {})
                    if base_token:
                        print(f"     Base token: {base_token}")
                print()
        else:
            print("   No pools to test extraction")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n✅ API testing complete!")

if __name__ == "__main__":
    asyncio.run(test_api_methods())
