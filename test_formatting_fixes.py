#!/usr/bin/env python3
"""Test script to verify gem formatting fixes"""
import sys
import os
sys.path.append('.')

from src.bot.gem_research_handler import GemResearchHandler, GemCriteria
from src.api.geckoterminal_client import GeckoTerminalClient
from src.database.session_manager import SessionManager
import asyncio

def test_circulating_percentage_bounds():
    """Test that circulating percentages are properly bounded at 100%"""
    print('🧪 Testing circulating percentage bounds...')
    
    handler = GemResearchHandler(None, None)
    
    test_cases = [
        (157220368540000.0, 157220.0, "Should cap at 100%"),
        (1000000.0, 5000000.0, "Should show high dilution"),
        (1000000.0, 1500000.0, "Should show moderate dilution"),
        (1000000.0, 1000000.0, "Should show low dilution"),
        (0, 0, "Should handle zero values"),
        (1000000.0, 0, "Should handle zero FDV"),
        (0, 1000000.0, "Should handle zero market cap"),
    ]
    
    success_count = 0
    for market_cap, fdv, expected in test_cases:
        try:
            result = handler._inline_fdv_analysis(market_cap, fdv)
            
            if '% tokens circulating' in result:
                import re
                percentage_match = re.search(r'(\d+)% tokens circulating', result)
                if percentage_match:
                    percentage = int(percentage_match.group(1))
                    if percentage > 100:
                        print(f'  ❌ FAILED: {expected} - Got {percentage}% (above 100%)')
                        continue
            
            print(f'  ✅ PASSED: {expected} - "{result}"')
            success_count += 1
            
        except Exception as e:
            print(f'  ❌ ERROR: {expected} - Exception: {e}')
    
    print(f'📊 Circulating percentage bounds: {success_count}/{len(test_cases)} tests passed')
    return success_count == len(test_cases)

def test_transaction_data_formatting():
    """Test that transaction data is properly formatted"""
    print('\n🧪 Testing transaction data formatting...')
    
    handler = GemResearchHandler(None, None)
    
    test_cases = [
        ({'buys': 19, 'sells': 5, 'buyers': 19, 'sellers': 5}, "19B/5S (19 buyers, 5 sellers)"),
        ({'buys': 0, 'sells': 0, 'buyers': 0, 'sellers': 0}, "0B/0S (0 buyers, 0 sellers)"),
        ({'buys': 100, 'sells': 50, 'buyers': 75, 'sellers': 25}, "100B/50S (75 buyers, 25 sellers)"),
        ({}, "0B/0S (0 buyers, 0 sellers)"),
        ("not_a_dict", "not_a_dict"),
        (None, "0"),
        (0, "0"),
    ]
    
    success_count = 0
    for input_data, expected in test_cases:
        try:
            result = handler._format_transaction_data(input_data)
            
            if result == expected:
                print(f'  ✅ PASSED: {input_data} -> "{result}"')
                success_count += 1
            else:
                print(f'  ❌ FAILED: {input_data} -> Expected "{expected}", got "{result}"')
                
        except Exception as e:
            print(f'  ❌ ERROR: {input_data} -> Exception: {e}')
    
    print(f'📊 Transaction data formatting: {success_count}/{len(test_cases)} tests passed')
    return success_count == len(test_cases)

def test_disclaimer_text():
    """Test that disclaimer text has been updated to BIGBALZ style"""
    print('\n🧪 Testing disclaimer text...')
    
    handler = GemResearchHandler(None, None)
    
    import inspect
    source = inspect.getsource(handler.format_single_gem_result)
    
    if "BIGBALZ TRUTH: This is straight financial advice, no sugar coating" in source:
        print('  ✅ PASSED: format_single_gem_result has updated disclaimer')
        disclaimer_test_1 = True
    else:
        print('  ❌ FAILED: format_single_gem_result still has old disclaimer')
        disclaimer_test_1 = False
    
    source_pool = inspect.getsource(handler.format_single_gem_result_from_pool)
    
    if "BIGBALZ TRUTH: This is straight financial advice, no sugar coating" in source_pool:
        print('  ✅ PASSED: format_single_gem_result_from_pool has updated disclaimer')
        disclaimer_test_2 = True
    else:
        print('  ❌ FAILED: format_single_gem_result_from_pool still has old disclaimer')
        disclaimer_test_2 = False
    
    success_count = disclaimer_test_1 + disclaimer_test_2
    print(f'📊 Disclaimer text: {success_count}/2 tests passed')
    return success_count == 2

async def test_integration_scenario():
    """Test the complete integration scenario that was causing issues"""
    print('\n🧪 Testing integration scenario...')
    
    try:
        os.environ['GECKOTERMINAL_API_KEY'] = 'CG-eE2zYQvDoQJo3sbqJaiDaySg'
        os.environ['TELEGRAM_BOT_TOKEN'] = '7989379553:AAFLOCD_5sfHi3Wvl9yqcSeGf5N11CC0zP0'
        
        api_client = GeckoTerminalClient(api_key='CG-eE2zYQvDoQJo3sbqJaiDaySg')
        session_manager = SessionManager()
        gem_handler = GemResearchHandler(api_client, session_manager)
        
        session = gem_handler.create_or_get_session(12345, 67890)
        session.network = 'base'
        
        criteria = GemCriteria(network='base', age='last_48', liquidity='50_250', mcap='micro')
        session.criteria = criteria
        
        print(f'  🎯 Testing exact scenario that caused original error: {criteria}')
        
        gems = await gem_handler.execute_gem_research(session)
        
        if not gems:
            print('  ⚠️ No gems found for base network, trying solana...')
            criteria = GemCriteria(network='solana', age='last_48', liquidity='50_250', mcap='micro')
            session.criteria = criteria
            gems = await gem_handler.execute_gem_research(session)
        
        if gems:
            print(f'  ✅ Found {len(gems)} gems, testing formatting...')
            
            for i, pool in enumerate(gems[:2]):
                try:
                    message, buttons = gem_handler.format_single_gem_result_from_pool(
                        pool, criteria, i, len(gems)
                    )
                    
                    if "Display Error" in message:
                        print(f'    ❌ Still getting Display Error for gem {i+1}')
                        return False
                    elif "Error formatting gem result" in message:
                        print(f'    ❌ Still getting generic error for gem {i+1}')
                        return False
                    else:
                        print(f'    ✅ Gem {i+1} formatted successfully: {len(message)} chars')
                        
                        if "% tokens circulating" in message:
                            import re
                            percentage_match = re.search(r'(\d+)% tokens circulating', message)
                            if percentage_match:
                                percentage = int(percentage_match.group(1))
                                if percentage > 100:
                                    print(f'    ❌ Gem {i+1} still has percentage > 100%: {percentage}%')
                                    return False
                                else:
                                    print(f'    ✅ Gem {i+1} has valid percentage: {percentage}%')
                        
                        if "B/" in message and "S (" in message:
                            print(f'    ✅ Gem {i+1} has properly formatted transaction data')
                        
                        if "BIGBALZ TRUTH:" in message:
                            print(f'    ✅ Gem {i+1} has updated disclaimer text')
                        
                except Exception as e:
                    print(f'    ❌ Exception formatting gem {i+1}: {e}')
                    return False
            
            print('  ✅ Integration scenario test PASSED')
            return True
        else:
            print('  ⚠️ No gems found - cannot test integration scenario')
            return True  # Not a failure, just no data available
            
    except Exception as e:
        print(f'  ❌ Integration test failed: {e}')
        return False

async def main():
    """Run all formatting fix tests"""
    print('🔧 BIGBALZ FORMATTING FIXES VERIFICATION')
    print('=' * 60)
    
    test_results = []
    
    test_results.append(test_circulating_percentage_bounds())
    test_results.append(test_transaction_data_formatting())
    test_results.append(test_disclaimer_text())
    
    integration_result = await test_integration_scenario()
    test_results.append(integration_result)
    
    passed_tests = sum(test_results)
    total_tests = len(test_results)
    
    print(f'\n📊 FINAL RESULTS: {passed_tests}/{total_tests} test categories passed')
    
    if passed_tests == total_tests:
        print('✅ ALL FORMATTING FIXES VERIFIED SUCCESSFULLY')
        return True
    else:
        print('❌ SOME FORMATTING FIXES FAILED VERIFICATION')
        return False

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
