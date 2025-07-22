#!/usr/bin/env python3
"""
Test the complete gem research flow with the fixes applied
"""
import sys
import os
sys.path.append('.')

from src.bot.gem_research_handler import GemResearchHandler, GemCriteria
from src.api.geckoterminal_client import GeckoTerminalClient
from src.database.session_manager import SessionManager
import asyncio

async def test_complete_flow():
    print('🔍 TESTING COMPLETE GEM RESEARCH FLOW WITH FIXES')
    print('=' * 60)
    
    try:
        os.environ['GECKOTERMINAL_API_KEY'] = 'CG-eE2zYQvDoQJo3sbqJaiDaySg'
        os.environ['TELEGRAM_BOT_TOKEN'] = '7989379553:AAFLOCD_5sfHi3Wvl9yqcSeGf5N11CC0zP0'
        
        api_client = GeckoTerminalClient(api_key='CG-eE2zYQvDoQJo3sbqJaiDaySg')
        session_manager = SessionManager()
        gem_handler = GemResearchHandler(api_client, session_manager)
        
        print('✓ Components initialized')
        
        print('\n🌐 TESTING BASE + LAST 48 HOURS (USER REPORTED ISSUE)')
        print('-' * 50)
        
        session = gem_handler.create_or_get_session(99999, 88888)
        session.network = 'base'
        
        print(f'✓ Session created: network={session.network}')
        
        await gem_handler.handle_age_selection(session, 'last_48')
        
        if session.new_pools_list and len(session.new_pools_list) > 0:
            print(f"✅ SUCCESS: Found {len(session.new_pools_list)} pools for Base + last 48 hours")
            print("✅ User can now proceed to liquidity selection!")
            
            for i, pool in enumerate(session.new_pools_list[:3]):
                attrs = pool.get('attributes', {})
                name = attrs.get('name', 'unknown')
                created_at = attrs.get('pool_created_at', 'unknown')
                print(f"   Pool {i+1}: {name} (created: {created_at})")
            
            base_success = True
        else:
            print("❌ FAILED: No pools found for Base + last 48 hours")
            print("❌ User cannot proceed to liquidity selection")
            base_success = False
        
        print('\n🌐 TESTING BSC + LAST 48 HOURS (ALSO MENTIONED BY USER)')
        print('-' * 50)
        
        session2 = gem_handler.create_or_get_session(88888, 77777)
        session2.network = 'bsc'
        
        await gem_handler.handle_age_selection(session2, 'last_48')
        
        if session2.new_pools_list and len(session2.new_pools_list) > 0:
            print(f"✅ SUCCESS: Found {len(session2.new_pools_list)} pools for BSC + last 48 hours")
            print("✅ User can now proceed to liquidity selection!")
            
            for i, pool in enumerate(session2.new_pools_list[:3]):
                attrs = pool.get('attributes', {})
                name = attrs.get('name', 'unknown')
                created_at = attrs.get('pool_created_at', 'unknown')
                print(f"   Pool {i+1}: {name} (created: {created_at})")
            
            bsc_success = True
        else:
            print("❌ FAILED: No pools found for BSC + last 48 hours")
            print("❌ User cannot proceed to liquidity selection")
            bsc_success = False
        
        print('\n🌐 TESTING SOLANA + LAST 48 HOURS (FOR COMPARISON)')
        print('-' * 50)
        
        session3 = gem_handler.create_or_get_session(77777, 66666)
        session3.network = 'solana'
        
        await gem_handler.handle_age_selection(session3, 'last_48')
        
        if session3.new_pools_list and len(session3.new_pools_list) > 0:
            print(f"✅ SUCCESS: Found {len(session3.new_pools_list)} pools for Solana + last 48 hours")
            solana_success = True
        else:
            print("❌ FAILED: No pools found for Solana + last 48 hours")
            solana_success = False
        
        print('\n' + '=' * 60)
        print('🎯 COMPLETE FLOW TEST SUMMARY')
        print('=' * 60)
        
        if base_success:
            print('✅ BASE + LAST 48 HOURS: FIXED - User can proceed to liquidity selection')
        else:
            print('❌ BASE + LAST 48 HOURS: STILL BROKEN - User cannot proceed')
        
        if bsc_success:
            print('✅ BSC + LAST 48 HOURS: FIXED - User can proceed to liquidity selection')
        else:
            print('❌ BSC + LAST 48 HOURS: STILL BROKEN - User cannot proceed')
        
        if solana_success:
            print('✅ SOLANA + LAST 48 HOURS: Working as expected')
        else:
            print('⚠️ SOLANA + LAST 48 HOURS: Unexpected issue')
        
        overall_success = base_success and bsc_success
        
        if overall_success:
            print('\n🎉 ALL USER REPORTED ISSUES HAVE BEEN RESOLVED!')
            print('🎉 Users can now find recent pools on Base and BSC networks!')
        else:
            print('\n⚠️ Some issues remain - further investigation needed')
        
        return overall_success
        
    except Exception as e:
        print(f'❌ Test failed: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_complete_flow())
    if result:
        print('\n✅ Complete gem research flow test PASSED')
    else:
        print('\n❌ Complete gem research flow test FAILED')
