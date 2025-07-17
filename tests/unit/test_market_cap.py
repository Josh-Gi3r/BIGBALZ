#!/usr/bin/env python3
"""
Test manual market cap calculation and complete gem research flow
"""
import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(__file__))

async def test_manual_market_cap():
    """Test manual market cap calculation and gem research flow"""
    try:
        from src.api.geckoterminal_client import GeckoTerminalClient
        from src.bot.gem_research_handler import GemResearchHandler, GemResearchSession, GemCriteria
        
        print("✅ Imports successful")
        
        api_client = GeckoTerminalClient()
        gem_handler = GemResearchHandler(api_client, None, None)
        
        print("✅ Handlers initialized")
        
        print("\n🔍 Testing manual market cap calculation...")
        
        test_cases = [
            {
                'name': 'User failing criteria (should now work)',
                'criteria': GemCriteria(
                    network='base',
                    age='last_48',
                    liquidity='250_1000',
                    mcap='small'
                )
            },
            {
                'name': 'Micro cap Base fresh',
                'criteria': GemCriteria(
                    network='base',
                    age='last_48',
                    liquidity='10_50',
                    mcap='micro'
                )
            },
            {
                'name': 'Solana micro cap',
                'criteria': GemCriteria(
                    network='solana',
                    age='last_48',
                    liquidity='50_250',
                    mcap='micro'
                )
            }
        ]
        
        for test_case in test_cases:
            print(f"\n🔍 Testing: {test_case['name']}")
            criteria = test_case['criteria']
            print(f"Criteria: {criteria.network}, {criteria.age}, {criteria.liquidity}, {criteria.mcap}")
            
            test_session = GemResearchSession(
                chat_id=12345,
                user_id=67890,
                step='results',
                criteria=criteria,
                new_pools_list=[],
                final_pools=[],
                current_index=0,
                timestamp=1234567890
            )
            
            try:
                await gem_handler.handle_age_selection(test_session, criteria.age)
                print(f"  After age selection: {len(test_session.new_pools_list)} pools")
                
                if test_session.new_pools_list:
                    results = await gem_handler.execute_gem_research(test_session)
                    print(f"  Final results: {len(results)} gems found")
                    
                    if results:
                        print(f"  ✅ SUCCESS: Found {len(results)} gems!")
                        
                        for i, pool in enumerate(results[:3]):
                            attrs = pool.get('attributes', {})
                            contract = gem_handler._extract_contract_from_pool(pool)
                            market_cap = attrs.get('market_cap_usd', 'N/A')
                            
                            print(f"    Gem {i+1}: {attrs.get('base_token_symbol', 'N/A')} ({contract})")
                            print(f"      - Liquidity: ${attrs.get('reserve_in_usd', 'N/A')}")
                            print(f"      - Market Cap: ${market_cap}")
                            
                            if market_cap != 'N/A' and market_cap is not None:
                                try:
                                    mcap_val = float(market_cap)
                                    if mcap_val > 0:
                                        print(f"      - ✅ Market cap calculated/available: ${mcap_val:,.0f}")
                                except:
                                    pass
                    else:
                        print(f"  ❌ No gems found")
                        
                        print(f"    Debugging filters...")
                        
                        liq_filtered = gem_handler._filter_pools_by_liquidity(test_session.new_pools_list, criteria.liquidity)
                        print(f"    After liquidity filter: {len(liq_filtered)} pools")
                        
                        mcap_filtered = gem_handler._filter_pools_by_market_cap(liq_filtered, criteria.mcap)
                        print(f"    After market cap filter: {len(mcap_filtered)} pools")
                        
                        if liq_filtered and not mcap_filtered:
                            print(f"    Issue: Market cap filter removing all pools")
                            for pool in liq_filtered[:3]:
                                attrs = pool.get('attributes', {})
                                token_data = pool.get('_token_data', {})
                                price = attrs.get('base_token_price_usd', 0)
                                supply = token_data.get('total_supply', 0)
                                mcap = attrs.get('market_cap_usd')
                                
                                print(f"      Pool: {attrs.get('base_token_symbol', 'N/A')}")
                                print(f"        - Price: ${price}")
                                print(f"        - Supply: {supply}")
                                print(f"        - Original MCap: {mcap}")
                                
                                if price and supply:
                                    try:
                                        calc_mcap = float(price) * float(supply)
                                        print(f"        - Calculated MCap: ${calc_mcap:,.0f}")
                                    except:
                                        print(f"        - Calculation failed")
                else:
                    print(f"  ❌ No pools fetched during age selection")
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")
                import traceback
                traceback.print_exc()
        
        print("\n🎉 Manual market cap test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_manual_market_cap())
    sys.exit(0 if success else 1)
