#!/usr/bin/env python3
"""
Test the execution logic fix for gem research
"""
import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(__file__))

async def test_execution_fix():
    """Test that execution logic uses pre-filtered pools correctly"""
    try:
        from src.api.geckoterminal_client import GeckoTerminalClient
        from src.bot.gem_research_handler import GemResearchHandler, GemResearchSession, GemCriteria
        
        print("✅ Testing execution logic fix...")
        
        api_client = GeckoTerminalClient()
        gem_handler = GemResearchHandler(api_client, None, None)
        
        network = 'base'
        
        print(f"\n🆕 Testing 'last_48' complete flow...")
        fresh_session = GemResearchSession(
            chat_id=12345,
            user_id=67890,
            step='age',
            criteria=GemCriteria(network=network, age='', liquidity='', mcap=''),
            new_pools_list=[],
            final_pools=[],
            current_index=0,
            timestamp=1234567890
        )
        
        await gem_handler.handle_age_selection(fresh_session, 'last_48')
        fresh_session.criteria.liquidity = '250_1000'
        fresh_session.criteria.mcap = 'small'
        
        fresh_results = await gem_handler.execute_gem_research(fresh_session)
        print(f"  Fresh results: {len(fresh_results)} gems")
        
        print(f"\n📅 Testing 'older_2_days' complete flow...")
        older_session = GemResearchSession(
            chat_id=12346,
            user_id=67891,
            step='age',
            criteria=GemCriteria(network=network, age='', liquidity='', mcap=''),
            new_pools_list=[],
            final_pools=[],
            current_index=0,
            timestamp=1234567890
        )
        
        await gem_handler.handle_age_selection(older_session, 'older_2_days')
        older_session.criteria.liquidity = '250_1000'
        older_session.criteria.mcap = 'small'
        
        older_results = await gem_handler.execute_gem_research(older_session)
        print(f"  Older results: {len(older_results)} gems")
        
        print(f"\n📊 EXECUTION FIX VERIFICATION:")
        print(f"  - Fresh gems found: {len(fresh_results)}")
        print(f"  - Older gems found: {len(older_results)}")
        
        if len(older_results) > 0:
            print(f"  ✅ SUCCESS: Older gems now found with user's criteria!")
            
            for i, pool in enumerate(older_results[:3]):
                attrs = pool.get('attributes', {})
                contract = gem_handler._extract_contract_from_pool(pool)
                market_cap = attrs.get('market_cap_usd', 'N/A')
                liquidity = attrs.get('reserve_in_usd', 'N/A')
                
                print(f"    Gem {i+1}: {attrs.get('base_token_symbol', 'N/A')} ({contract})")
                print(f"      - Liquidity: ${liquidity}")
                print(f"      - Market Cap: ${market_cap}")
        else:
            print(f"  ❌ ISSUE: Still no older gems found")
            
            print(f"\n🔍 Debugging filtering steps...")
            print(f"  - Pre-filtered pools: {len(older_session.new_pools_list)}")
            
            if len(older_session.new_pools_list) > 0:
                liq_filtered = gem_handler._filter_pools_by_liquidity(older_session.new_pools_list, '250_1000')
                print(f"  - After liquidity filter: {len(liq_filtered)}")
                
                if len(liq_filtered) > 0:
                    mcap_filtered = gem_handler._filter_pools_by_market_cap(liq_filtered, 'small')
                    print(f"  - After market cap filter: {len(mcap_filtered)}")
                    
                    if len(mcap_filtered) == 0:
                        print(f"  - Market cap filter is the bottleneck")
                        
                        for i, pool in enumerate(liq_filtered[:5]):
                            attrs = pool.get('attributes', {})
                            market_cap = attrs.get('market_cap_usd')
                            symbol = attrs.get('base_token_symbol', 'N/A')
                            
                            print(f"    Pool {i+1}: {symbol}")
                            print(f"      - Market Cap: {market_cap} (type: {type(market_cap)})")
                            
                            if market_cap is not None:
                                try:
                                    mcap_val = float(market_cap)
                                    in_range = 1000000 <= mcap_val <= 10000000
                                    print(f"      - Numeric: ${mcap_val:,.0f}, In range: {in_range}")
                                except:
                                    print(f"      - Cannot convert to float")
                else:
                    print(f"  - Liquidity filter is the bottleneck")
        
        print(f"\n🎉 Execution fix test completed!")
        return len(older_results) > 0
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_execution_fix())
    sys.exit(0 if success else 1)
