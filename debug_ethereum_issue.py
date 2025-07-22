#!/usr/bin/env python3
"""
Debug the Ethereum network issue to understand why new_pools endpoint fails
"""
import sys
import os
sys.path.append('.')

from src.api.geckoterminal_client import GeckoTerminalClient
import asyncio

async def debug_ethereum_issue():
    print('🔍 DEBUGGING ETHEREUM NETWORK ISSUE')
    print('=' * 50)
    
    try:
        os.environ['GECKOTERMINAL_API_KEY'] = 'CG-eE2zYQvDoQJo3sbqJaiDaySg'
        api_client = GeckoTerminalClient(api_key='CG-eE2zYQvDoQJo3sbqJaiDaySg')
        
        print('✓ API client initialized')
        
        ethereum_identifiers = ['ethereum', 'eth', 'mainnet']
        
        for network_id in ethereum_identifiers:
            print(f'\n🌐 TESTING NETWORK ID: {network_id}')
            print('-' * 30)
            
            try:
                trending = await api_client.get_trending_pools(network_id, "5m", 5)
                if trending and len(trending) > 0:
                    print(f"   ✅ get_trending_pools: {len(trending)} pools")
                else:
                    print(f"   ❌ get_trending_pools: No pools")
            except Exception as e:
                print(f"   ❌ get_trending_pools failed: {e}")
            
            try:
                new_pools = await api_client.get_new_pools_paginated(network_id, 5)
                if new_pools and len(new_pools) > 0:
                    print(f"   ✅ get_new_pools_paginated: {len(new_pools)} pools")
                else:
                    print(f"   ❌ get_new_pools_paginated: No pools")
            except Exception as e:
                print(f"   ❌ get_new_pools_paginated failed: {e}")
            
            try:
                new_pools_simple = await api_client.get_new_pools(network_id, 5)
                if new_pools_simple and len(new_pools_simple) > 0:
                    print(f"   ✅ get_new_pools: {len(new_pools_simple)} pools")
                else:
                    print(f"   ❌ get_new_pools: No pools")
            except Exception as e:
                print(f"   ❌ get_new_pools failed: {e}")
        
        print('\n' + '=' * 50)
        print('🎯 ETHEREUM DEBUG SUMMARY')
        print('=' * 50)
        print('This will help identify:')
        print('1. If Ethereum uses a different network identifier')
        print('2. If Ethereum supports new_pools endpoints at all')
        print('3. What fallback strategy we should use')
        
        return True
        
    except Exception as e:
        print(f'❌ Debug failed: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(debug_ethereum_issue())
    if result:
        print('\n✅ Ethereum debug completed')
    else:
        print('\n❌ Ethereum debug failed')
