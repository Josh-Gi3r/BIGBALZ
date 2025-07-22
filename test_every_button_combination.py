#!/usr/bin/env python3
"""
Comprehensive test of EVERY button combination in the gem research flow
Tests all networks, ages, liquidity levels, and market cap combinations
"""
import sys
import os
sys.path.append('.')

from src.bot.gem_research_handler import GemResearchHandler, GemCriteria
from src.api.geckoterminal_client import GeckoTerminalClient
from src.database.session_manager import SessionManager
import asyncio
import time

async def test_every_combination():
    print('🔍 COMPREHENSIVE TEST OF EVERY BUTTON COMBINATION')
    print('=' * 80)
    
    try:
        os.environ['GECKOTERMINAL_API_KEY'] = 'CG-eE2zYQvDoQJo3sbqJaiDaySg'
        os.environ['TELEGRAM_BOT_TOKEN'] = '7989379553:AAFLOCD_5sfHi3Wvl9yqcSeGf5N11CC0zP0'
        
        api_client = GeckoTerminalClient(api_key='CG-eE2zYQvDoQJo3sbqJaiDaySg')
        session_manager = SessionManager()
        gem_handler = GemResearchHandler(api_client, session_manager)
        
        print('✓ Components initialized')
        
        networks = ['solana', 'base', 'bsc', 'eth']
        
        ages = ['last_48', 'older_2_days']
        
        liquidity_levels = ['10_50', '50_250', '250_1000', '1000_plus']
        
        mcap_levels = ['micro', 'small', 'mid']
        
        results = []
        total_tests = len(networks) * len(ages) * len(liquidity_levels) * len(mcap_levels)
        current_test = 0
        
        print(f'\n🎯 TESTING {total_tests} TOTAL COMBINATIONS')
        print('=' * 80)
        
        for network in networks:
            print(f'\n🌐 TESTING NETWORK: {network.upper()}')
            print('-' * 60)
            
            for age in ages:
                print(f'\n  📅 Age: {age}')
                
                session = gem_handler.create_or_get_session(current_test + 10000, current_test + 20000)
                session.network = network
                
                try:
                    await gem_handler.handle_age_selection(session, age)
                    
                    if session.new_pools_list and len(session.new_pools_list) > 0:
                        pools_found = len(session.new_pools_list)
                        print(f'    ✅ {network} + {age}: {pools_found} pools found')
                        age_success = True
                    else:
                        print(f'    ❌ {network} + {age}: No pools found')
                        age_success = False
                        
                except Exception as e:
                    print(f'    ❌ {network} + {age}: ERROR - {e}')
                    age_success = False
                
                if not age_success:
                    for liquidity in liquidity_levels:
                        for mcap in mcap_levels:
                            current_test += 1
                            results.append({
                                'network': network,
                                'age': age,
                                'liquidity': liquidity,
                                'mcap': mcap,
                                'status': 'FAILED_AT_AGE',
                                'pools_found': 0,
                                'gems_found': 0
                            })
                    continue
                
                for liquidity in liquidity_levels:
                    for mcap in mcap_levels:
                        current_test += 1
                        
                        try:
                            if session.criteria is None:
                                session.criteria = GemCriteria(network=network, age=age, liquidity='', mcap='')
                            session.criteria.liquidity = liquidity
                            session.criteria.mcap = mcap
                            session.step = 'results'
                            
                            gems = await gem_handler.execute_gem_research(session)
                            
                            if not gems:
                                results.append({
                                    'network': network,
                                    'age': age,
                                    'liquidity': liquidity,
                                    'mcap': mcap,
                                    'status': 'NO_GEMS_FOUND',
                                    'pools_found': pools_found,
                                    'gems_found': 0
                                })
                                print(f'      ⚠️ {liquidity} liquidity + {mcap} mcap: No gems found')
                                continue
                            
                            gems_found = len(gems)
                            results.append({
                                'network': network,
                                'age': age,
                                'liquidity': liquidity,
                                'mcap': mcap,
                                'status': 'SUCCESS',
                                'pools_found': pools_found,
                                'gems_found': gems_found
                            })
                            
                            print(f'      ✅ {liquidity} liquidity + {mcap} mcap: {gems_found} gems')
                            
                        except Exception as e:
                            results.append({
                                'network': network,
                                'age': age,
                                'liquidity': liquidity,
                                'mcap': mcap,
                                'status': f'ERROR: {str(e)[:50]}',
                                'pools_found': pools_found if 'pools_found' in locals() else 0,
                                'gems_found': 0
                            })
                            print(f'      ❌ {liquidity} liquidity + {mcap} mcap: ERROR - {e}')
                
                await asyncio.sleep(1)
        
        print('\n' + '=' * 80)
        print('🎯 COMPREHENSIVE TEST RESULTS')
        print('=' * 80)
        
        success_count = len([r for r in results if r['status'] == 'SUCCESS'])
        total_count = len(results)
        
        print(f'📊 OVERALL SUCCESS RATE: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)')
        
        for network in networks:
            network_results = [r for r in results if r['network'] == network]
            network_success = len([r for r in network_results if r['status'] == 'SUCCESS'])
            
            print(f'\n🌐 {network.upper()}: {network_success}/{len(network_results)} combinations working')
            
            for age in ages:
                age_results = [r for r in network_results if r['age'] == age]
                age_success = len([r for r in age_results if r['status'] == 'SUCCESS'])
                
                if age_success == 0:
                    print(f'   ❌ {age}: 0/{len(age_results)} - COMPLETELY BROKEN')
                elif age_success == len(age_results):
                    print(f'   ✅ {age}: {age_success}/{len(age_results)} - FULLY WORKING')
                else:
                    print(f'   ⚠️ {age}: {age_success}/{len(age_results)} - PARTIALLY WORKING')
        
        print('\n🚨 CRITICAL FAILURES (No pools found at age selection):')
        age_failures = [r for r in results if r['status'] == 'FAILED_AT_AGE']
        if age_failures:
            for failure in age_failures:
                print(f'   ❌ {failure["network"]} + {failure["age"]}: No pools found')
        else:
            print('   ✅ No critical age selection failures!')
        
        print('\n💎 GEM DETECTION ISSUES:')
        no_gems_found = [r for r in results if r['status'] == 'NO_GEMS_FOUND']
        if no_gems_found:
            print(f'   ⚠️ {len(no_gems_found)} combinations found pools but no gems after filtering')
            for failure in no_gems_found[:5]:  # Show first 5
                print(f'     - {failure["network"]} + {failure["age"]} + {failure["liquidity"]} + {failure["mcap"]}: {failure["pools_found"]} pools → 0 gems')
            if len(no_gems_found) > 5:
                print(f'     ... and {len(no_gems_found) - 5} more combinations with no gems')
        else:
            print('   ✅ All combinations that found pools also detected gems!')
        
        print('\n✅ FULLY WORKING COMBINATIONS:')
        working = [r for r in results if r['status'] == 'SUCCESS' and r['gems_found'] > 0]
        if working:
            for combo in working[:10]:  # Show first 10
                print(f'   ✅ {combo["network"]} + {combo["age"]} + {combo["liquidity"]} + {combo["mcap"]}: {combo["gems_found"]} gems')
            if len(working) > 10:
                print(f'   ... and {len(working) - 10} more working combinations')
        else:
            print('   ❌ NO FULLY WORKING COMBINATIONS FOUND!')
        
        return success_count > 0
        
    except Exception as e:
        print(f'❌ Comprehensive test failed: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_every_combination())
    if result:
        print('\n✅ Some combinations are working')
    else:
        print('\n❌ NO combinations are working - major issues detected')
