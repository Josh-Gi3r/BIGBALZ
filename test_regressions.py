#!/usr/bin/env python3
"""
Test for regressions in other functionality after the fixes
"""
import sys
import os
sys.path.append('.')

from src.bot.gem_research_handler import GemResearchHandler, GemCriteria
from src.api.geckoterminal_client import GeckoTerminalClient
from src.database.session_manager import SessionManager
import asyncio

async def test_regressions():
    print('🔍 TESTING FOR REGRESSIONS IN OTHER FUNCTIONALITY')
    print('=' * 60)
    
    try:
        os.environ['GECKOTERMINAL_API_KEY'] = 'CG-eE2zYQvDoQJo3sbqJaiDaySg'
        os.environ['TELEGRAM_BOT_TOKEN'] = '7989379553:AAFLOCD_5sfHi3Wvl9yqcSeGf5N11CC0zP0'
        
        api_client = GeckoTerminalClient(api_key='CG-eE2zYQvDoQJo3sbqJaiDaySg')
        session_manager = SessionManager()
        gem_handler = GemResearchHandler(api_client, session_manager)
        
        print('✓ Components initialized')
        
        print('\n🕐 TESTING "OLDER_2_DAYS" AGE SELECTION')
        print('-' * 40)
        
        session1 = gem_handler.create_or_get_session(11111, 22222)
        session1.network = 'base'
        
        await gem_handler.handle_age_selection(session1, 'older_2_days')
        
        if session1.new_pools_list and len(session1.new_pools_list) > 0:
            print(f"✅ older_2_days works: Found {len(session1.new_pools_list)} pools")
            older_2_days_success = True
        else:
            print("❌ older_2_days broken: No pools found")
            older_2_days_success = False
        
        print('\n🌐 TESTING ETHEREUM NETWORK')
        print('-' * 40)
        
        session2 = gem_handler.create_or_get_session(22222, 33333)
        session2.network = 'ethereum'
        
        await gem_handler.handle_age_selection(session2, 'last_48')
        
        if session2.new_pools_list and len(session2.new_pools_list) > 0:
            print(f"✅ Ethereum works: Found {len(session2.new_pools_list)} pools")
            ethereum_success = True
        else:
            print("❌ Ethereum broken: No pools found")
            ethereum_success = False
        
        print('\n🌐 TESTING SOLANA NETWORK (SHOULD HAVE MANY RECENT POOLS)')
        print('-' * 40)
        
        session3 = gem_handler.create_or_get_session(33333, 44444)
        session3.network = 'solana'
        
        await gem_handler.handle_age_selection(session3, 'last_48')
        
        if session3.new_pools_list and len(session3.new_pools_list) > 0:
            print(f"✅ Solana works: Found {len(session3.new_pools_list)} pools")
            solana_success = True
        else:
            print("❌ Solana broken: No pools found")
            solana_success = False
        
        print('\n📡 TESTING API CLIENT METHODS INDEPENDENTLY')
        print('-' * 40)
        
        trending = await api_client.get_trending_pools('solana', '5m', 10)
        if trending and len(trending) > 0:
            print(f"✅ get_trending_pools works: {len(trending)} pools")
            trending_success = True
        else:
            print("❌ get_trending_pools broken")
            trending_success = False
        
        new_pools = await api_client.get_new_pools_paginated('base', 10)
        if new_pools and len(new_pools) > 0:
            print(f"✅ get_new_pools_paginated works: {len(new_pools)} pools")
            new_pools_paginated_success = True
        else:
            print("❌ get_new_pools_paginated broken")
            new_pools_paginated_success = False
        
        new_pools_simple = await api_client.get_new_pools('bsc', 10)
        if new_pools_simple and len(new_pools_simple) > 0:
            print(f"✅ get_new_pools (fixed) works: {len(new_pools_simple)} pools")
            new_pools_simple_success = True
        else:
            print("❌ get_new_pools (fixed) broken")
            new_pools_simple_success = False
        
        print('\n' + '=' * 60)
        print('🎯 REGRESSION TEST SUMMARY')
        print('=' * 60)
        
        all_tests = [
            ("older_2_days age selection", older_2_days_success),
            ("Ethereum network", ethereum_success),
            ("Solana network", solana_success),
            ("get_trending_pools", trending_success),
            ("get_new_pools_paginated", new_pools_paginated_success),
            ("get_new_pools (fixed)", new_pools_simple_success)
        ]
        
        passed_tests = 0
        for test_name, success in all_tests:
            if success:
                print(f"✅ {test_name}: PASSED")
                passed_tests += 1
            else:
                print(f"❌ {test_name}: FAILED")
        
        overall_success = passed_tests == len(all_tests)
        
        print(f"\n📊 RESULTS: {passed_tests}/{len(all_tests)} tests passed")
        
        if overall_success:
            print("🎉 NO REGRESSIONS DETECTED - All functionality working correctly!")
        else:
            print("⚠️ REGRESSIONS DETECTED - Some functionality broken by changes")
        
        return overall_success
        
    except Exception as e:
        print(f'❌ Regression test failed: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_regressions())
    if result:
        print('\n✅ Regression test PASSED - No regressions detected')
    else:
        print('\n❌ Regression test FAILED - Regressions detected')
