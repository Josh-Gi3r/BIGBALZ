#!/usr/bin/env python3
"""
Test age filtering logic for gem research
"""
import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(__file__))

async def test_age_filtering():
    """Test age filtering for fresh vs older tokens"""
    try:
        from src.api.geckoterminal_client import GeckoTerminalClient
        from src.bot.gem_research_handler import GemResearchHandler, GemResearchSession, GemCriteria
        
        print("✅ Imports successful")
        
        api_client = GeckoTerminalClient()
        gem_handler = GemResearchHandler(api_client, None, None)
        
        print("✅ Handlers initialized")
        
        print("\n🔍 Testing age filtering logic...")
        
        network = 'base'
        
        print(f"\n📅 Testing 'last_48' age selection for {network}...")
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
        fresh_count = len(fresh_session.new_pools_list)
        print(f"  Fresh pools found: {fresh_count}")
        
        print(f"\n📅 Testing 'older_2_days' age selection for {network}...")
        older_session = GemResearchSession(
            chat_id=12345,
            user_id=67890,
            step='age',
            criteria=GemCriteria(network=network, age='', liquidity='', mcap=''),
            new_pools_list=[],
            final_pools=[],
            current_index=0,
            timestamp=1234567890
        )
        
        await gem_handler.handle_age_selection(older_session, 'older_2_days')
        older_count = len(older_session.new_pools_list)
        print(f"  Older pools found: {older_count}")
        
        if fresh_count > 0 and older_count > 0:
            print(f"\n✅ SUCCESS: Both age filters return results")
            print(f"  - Fresh launches: {fresh_count} pools")
            print(f"  - Older tokens: {older_count} pools")
            
            fresh_contracts = set()
            for pool in fresh_session.new_pools_list[:10]:
                contract = gem_handler._extract_contract_from_pool(pool)
                if contract:
                    fresh_contracts.add(contract)
            
            older_contracts = set()
            for pool in older_session.new_pools_list[:10]:
                contract = gem_handler._extract_contract_from_pool(pool)
                if contract:
                    older_contracts.add(contract)
            
            overlap = fresh_contracts.intersection(older_contracts)
            print(f"  - Contract overlap: {len(overlap)} (should be 0)")
            
            if len(overlap) == 0:
                print(f"  ✅ Perfect separation - no overlap between fresh and older pools")
            else:
                print(f"  ⚠️ Some overlap detected - filtering may need refinement")
                
        else:
            print(f"\n❌ ISSUE: One or both age filters returned no results")
            print(f"  - Fresh: {fresh_count}, Older: {older_count}")
        
        print(f"\n🔍 Testing complete gem research flow with older tokens...")
        
        test_criteria = GemCriteria(
            network='base',
            age='older_2_days',
            liquidity='250_1000',
            mcap='small'
        )
        
        older_session.criteria = test_criteria
        results = await gem_handler.execute_gem_research(older_session)
        
        print(f"  Final results for older Base tokens ($250K-$1M liq, small mcap): {len(results)} gems")
        
        if results:
            print(f"  ✅ SUCCESS: Found {len(results)} older gems!")
            for i, pool in enumerate(results[:3]):
                attrs = pool.get('attributes', {})
                contract = gem_handler._extract_contract_from_pool(pool)
                market_cap = attrs.get('market_cap_usd', 'N/A')
                
                print(f"    Gem {i+1}: {attrs.get('base_token_symbol', 'N/A')} ({contract})")
                print(f"      - Liquidity: ${attrs.get('reserve_in_usd', 'N/A')}")
                print(f"      - Market Cap: ${market_cap}")
        else:
            print(f"  ❌ No older gems found with specified criteria")
        
        print("\n🎉 Age filtering test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_age_filtering())
    sys.exit(0 if success else 1)
