#!/usr/bin/env python3
"""
Final test of gem research API with all fixes applied
"""
import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(__file__))

async def test_final_gem_research():
    """Test the complete gem research flow with all fixes"""
    try:
        from src.api.geckoterminal_client import GeckoTerminalClient
        from src.bot.gem_research_handler import GemResearchHandler, GemResearchSession, GemCriteria
        
        print("✅ Imports successful")
        
        api_client = GeckoTerminalClient()
        gem_handler = GemResearchHandler(api_client, None, None)
        
        print("✅ Handlers initialized")
        
        test_combinations = [
            {
                'name': 'User failing criteria',
                'criteria': GemCriteria(
                    network='base',
                    age='last_48',
                    liquidity='250_1000',  # $250K-$1M
                    mcap='small'  # $1M-$10M
                )
            },
            {
                'name': 'Micro cap Base',
                'criteria': GemCriteria(
                    network='base',
                    age='last_48',
                    liquidity='10_50',  # $10K-$50K
                    mcap='micro'  # Under $1M (includes None values)
                )
            },
            {
                'name': 'Solana micro cap',
                'criteria': GemCriteria(
                    network='solana',
                    age='last_48',
                    liquidity='50_250',  # $50K-$250K
                    mcap='micro'  # Under $1M (includes None values)
                )
            }
        ]
        
        for test_case in test_combinations:
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
                            print(f"    Gem {i+1}: {attrs.get('base_token_symbol', 'N/A')} ({contract})")
                            print(f"      - Liquidity: ${attrs.get('reserve_in_usd', 'N/A')}")
                            print(f"      - Market Cap: ${attrs.get('market_cap_usd', 'N/A')}")
                    else:
                        print(f"  ❌ No gems found")
                        
                        print(f"    Debugging filters...")
                        
                        liq_filtered = gem_handler._filter_pools_by_liquidity(test_session.new_pools_list, criteria.liquidity)
                        print(f"    After liquidity filter: {len(liq_filtered)} pools")
                        
                        mcap_filtered = gem_handler._filter_pools_by_market_cap(liq_filtered, criteria.mcap)
                        print(f"    After market cap filter: {len(mcap_filtered)} pools")
                        
                        if mcap_filtered:
                            print(f"    Sample filtered pools:")
                            for pool in mcap_filtered[:2]:
                                attrs = pool.get('attributes', {})
                                print(f"      - {attrs.get('base_token_symbol', 'N/A')}: ${attrs.get('reserve_in_usd', 'N/A')} liq, ${attrs.get('market_cap_usd', 'N/A')} mcap")
                else:
                    print(f"  ❌ No pools fetched during age selection")
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n🔍 Testing age selection logic fix...")
        
        test_session = GemResearchSession(
            chat_id=12345,
            user_id=67890,
            step='results',
            criteria=GemCriteria(
                network='solana',
                age='older_2_days',
                liquidity='50_250',
                mcap='micro'
            ),
            new_pools_list=[],
            final_pools=[],
            current_index=0,
            timestamp=1234567890
        )
        
        print(f"Testing 'older than 2 days' age selection...")
        await gem_handler.handle_age_selection(test_session, 'older_2_days')
        print(f"After 'older_2_days' selection: {len(test_session.new_pools_list)} pools")
        
        if test_session.new_pools_list:
            results = await gem_handler.execute_gem_research(test_session)
            print(f"'Older than 2 days' results: {len(results)} gems found")
        
        print("\n🎉 Final gem research test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_final_gem_research())
    sys.exit(0 if success else 1)
