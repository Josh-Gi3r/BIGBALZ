#!/usr/bin/env python3
"""
Test the updated API methods to verify gem research fixes work
"""
import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(__file__))

async def test_api_fixes():
    """Test the updated gem research API methods"""
    try:
        from src.api.geckoterminal_client import GeckoTerminalClient
        from src.bot.gem_research_handler import GemResearchHandler, GemResearchSession, GemCriteria
        
        print("✅ Imports successful")
        
        api_client = GeckoTerminalClient()
        gem_handler = GemResearchHandler(api_client, None, None)
        
        print("✅ Handlers initialized")
        
        print("\n🔍 Testing updated new pools API...")
        
        networks_to_test = ['base', 'solana']
        
        for network in networks_to_test:
            print(f"\n--- Testing {network} network ---")
            
            try:
                new_pools = await api_client.get_new_pools_paginated(network, max_pools=50)
                print(f"✅ {network}: Fetched {len(new_pools)} new pools")
                
                if new_pools:
                    sample_pool = new_pools[0]
                    attrs = sample_pool.get('attributes', {})
                    print(f"  Sample pool:")
                    print(f"    - Symbol: {attrs.get('base_token_symbol', 'N/A')}")
                    print(f"    - Network: {attrs.get('network', 'N/A')}")
                    print(f"    - Liquidity: ${attrs.get('reserve_in_usd', 'N/A')}")
                    print(f"    - Market Cap: ${attrs.get('market_cap_usd', 'N/A')}")
                    print(f"    - FDV: ${attrs.get('fdv_usd', 'N/A')}")
                    
                    contract = gem_handler._extract_contract_from_pool(sample_pool)
                    print(f"    - Contract: {contract}")
                    
                    liq_ranges = {
                        '10K-50K': 0,
                        '50K-250K': 0, 
                        '250K-1M': 0,
                        '1M+': 0
                    }
                    
                    mcap_ranges = {
                        'micro (<$1M)': 0,
                        'small ($1M-$10M)': 0,
                        'mid ($10M+)': 0,
                        'no_data': 0
                    }
                    
                    for pool in new_pools:
                        pool_attrs = pool.get('attributes', {})
                        
                        try:
                            liquidity = float(pool_attrs.get('reserve_in_usd', 0))
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
                        
                        try:
                            mcap = pool_attrs.get('market_cap_usd')
                            if mcap is None:
                                mcap_ranges['no_data'] += 1
                            else:
                                mcap = float(mcap)
                                if mcap < 1000000:
                                    mcap_ranges['micro (<$1M)'] += 1
                                elif mcap < 10000000:
                                    mcap_ranges['small ($1M-$10M)'] += 1
                                else:
                                    mcap_ranges['mid ($10M+)'] += 1
                        except (ValueError, TypeError):
                            mcap_ranges['no_data'] += 1
                    
                    print(f"  Liquidity distribution:")
                    for range_name, count in liq_ranges.items():
                        print(f"    - {range_name}: {count} pools")
                    
                    print(f"  Market cap distribution:")
                    for range_name, count in mcap_ranges.items():
                        print(f"    - {range_name}: {count} pools")
                        
                else:
                    print(f"❌ {network}: No pools returned")
                    
            except Exception as e:
                print(f"❌ {network}: API call failed - {e}")
                import traceback
                traceback.print_exc()
        
        print("\n🔍 Testing complete gem research flow with user's failing criteria...")
        
        test_session = GemResearchSession(
            chat_id=12345,
            user_id=67890,
            step='results',
            criteria=GemCriteria(
                network='base',
                age='last_48',
                liquidity='250_1000',  # $250K-$1M
                mcap='small'  # $1M-$10M
            ),
            new_pools_list=[],
            final_pools=[],
            current_index=0,
            timestamp=1234567890
        )
        
        print(f"Testing criteria: {test_session.criteria.network}, {test_session.criteria.age}, {test_session.criteria.liquidity}, {test_session.criteria.mcap}")
        
        await gem_handler.handle_age_selection(test_session, test_session.criteria.age)
        print(f"After age selection: {len(test_session.new_pools_list)} pools")
        
        if test_session.new_pools_list:
            results = await gem_handler.execute_gem_research(test_session)
            print(f"Final results: {len(results)} gems found")
            
            if results:
                print("✅ SUCCESS: Found gems with user's criteria!")
                for i, pool in enumerate(results[:3]):
                    attrs = pool.get('attributes', {})
                    contract = gem_handler._extract_contract_from_pool(pool)
                    print(f"  Gem {i+1}: {attrs.get('base_token_symbol', 'N/A')} ({contract})")
                    print(f"    - Liquidity: ${attrs.get('reserve_in_usd', 'N/A')}")
                    print(f"    - Market Cap: ${attrs.get('market_cap_usd', 'N/A')}")
            else:
                print("❌ Still no gems found - investigating further...")
                
                print("\n🔍 Debugging filtering steps...")
                
                liq_filtered = gem_handler._filter_pools_by_liquidity(test_session.new_pools_list, '250_1000')
                print(f"After liquidity filter ($250K-$1M): {len(liq_filtered)} pools")
                
                if liq_filtered:
                    for pool in liq_filtered[:3]:
                        attrs = pool.get('attributes', {})
                        print(f"  - {attrs.get('base_token_symbol', 'N/A')}: ${attrs.get('reserve_in_usd', 'N/A')} liquidity")
                
                mcap_filtered = gem_handler._filter_pools_by_market_cap(liq_filtered, 'small')
                print(f"After market cap filter ($1M-$10M): {len(mcap_filtered)} pools")
                
                if mcap_filtered:
                    for pool in mcap_filtered[:3]:
                        attrs = pool.get('attributes', {})
                        print(f"  - {attrs.get('base_token_symbol', 'N/A')}: ${attrs.get('market_cap_usd', 'N/A')} mcap")
        else:
            print("❌ No pools fetched during age selection")
        
        print("\n🎉 API fix test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_api_fixes())
    sys.exit(0 if success else 1)
