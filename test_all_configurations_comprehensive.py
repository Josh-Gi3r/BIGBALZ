#!/usr/bin/env python3
"""Test all 96 gem research configurations across all networks"""
import asyncio
import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

async def test_complete_configuration_matrix():
    from api.geckoterminal_client import GeckoTerminalClient
    from bot.gem_research_handler import GemResearchHandler, GemCriteria
    
    api_client = GeckoTerminalClient()
    gem_handler = GemResearchHandler(api_client, None)
    
    networks = ['solana', 'ethereum', 'bsc', 'base']
    ages = ['last_48', 'older_2_days']
    liquidities = ['10_50', '50_250', '250_1000', '1000_plus']
    mcaps = ['micro', 'small', 'mid']
    
    config_names = {
        'ages': {'last_48': 'Last 48h', 'older_2_days': 'Older 2d'},
        'liquidities': {'10_50': '$10K-$50K', '50_250': '$50K-$250K', 
                       '250_1000': '$250K-$1M', '1000_plus': '$1M+'},
        'mcaps': {'micro': 'Micro(<$1M)', 'small': 'Small($1M-$10M)', 'mid': 'Mid($10M-$50M)'}
    }
    
    results_matrix = {}
    total_tests = 0
    successful_tests = 0
    
    print(f"🎯 COMPREHENSIVE GEM RESEARCH TESTING")
    print(f"Testing {len(networks)} networks × {len(ages)} ages × {len(liquidities)} liquidities × {len(mcaps)} mcaps = {len(networks)*len(ages)*len(liquidities)*len(mcaps)} configurations")
    print("=" * 80)
    
    for network in networks:
        print(f"\n🌐 TESTING {network.upper()} NETWORK")
        print("-" * 50)
        
        network_results = {}
        network_successes = 0
        
        for age in ages:
            for liquidity in liquidities:
                for mcap in mcaps:
                    total_tests += 1
                    config_key = f"{age}_{liquidity}_{mcap}"
                    config_display = f"{config_names['ages'][age]} + {config_names['liquidities'][liquidity]} + {config_names['mcaps'][mcap]}"
                    
                    print(f"  {total_tests:2d}. {config_display}")
                    print(f"      ", end="")
                    
                    try:
                        session = gem_handler.create_or_get_session(total_tests, 67890)
                        session.criteria = GemCriteria(
                            network=network,
                            age=age,
                            liquidity=liquidity,
                            mcap=mcap
                        )
                        
                        print("Fetching... ", end="")
                        await gem_handler.handle_age_selection(session, age)
                        
                        if hasattr(session, 'new_pools_list') and session.new_pools_list:
                            pool_count = len(session.new_pools_list)
                            print(f"✅{pool_count}p | ", end="")
                            
                            print("Filtering... ", end="")
                            results = await gem_handler.execute_gem_research(session)
                            gem_count = len(results)
                            
                            if gem_count > 0:
                                successful_tests += 1
                                network_successes += 1
                                print(f"✅ {gem_count} gems")
                                
                                sample = results[0]
                                attrs = sample.get('attributes', {})
                                symbol = attrs.get('base_token_symbol', 'UNKNOWN')
                                liquidity_val = float(attrs.get('reserve_in_usd', 0))
                                fdv_val = float(attrs.get('fdv_usd', 0))
                                
                                print(f"        Sample: {symbol} (${liquidity_val:,.0f}/${fdv_val:,.0f})")
                                
                                network_results[config_key] = {
                                    'status': 'success',
                                    'gems': gem_count,
                                    'pools': pool_count,
                                    'sample': f"{symbol} (${liquidity_val:,.0f}/${fdv_val:,.0f})"
                                }
                            else:
                                print(f"❌ 0 gems (filtered out)")
                                network_results[config_key] = {
                                    'status': 'no_results',
                                    'pools': pool_count,
                                    'gems': 0
                                }
                        else:
                            print(f"❌ No pools fetched")
                            network_results[config_key] = {
                                'status': 'no_pools',
                                'error': 'Pool fetching failed'
                            }
                            
                    except Exception as e:
                        error_msg = str(e)
                        print(f"💥 ERROR: {error_msg[:30]}...")
                        network_results[config_key] = {
                            'status': 'error',
                            'error': error_msg
                        }
                    
                    await asyncio.sleep(1.5)
            
            await asyncio.sleep(3)
        
        results_matrix[network] = network_results
        print(f"\n{network.upper()} Summary: {network_successes}/24 configurations successful")
        
        await asyncio.sleep(5)
    
    generate_comprehensive_report(results_matrix, total_tests, successful_tests, config_names)
    
    return results_matrix

def generate_comprehensive_report(results_matrix, total_tests, successful_tests, config_names):
    print(f"\n📊 COMPREHENSIVE TEST RESULTS")
    print("=" * 80)
    print(f"Total configurations tested: {total_tests}")
    print(f"Successful configurations: {successful_tests}")
    print(f"Overall success rate: {(successful_tests/total_tests)*100:.1f}%")
    
    print(f"\n📈 NETWORK PERFORMANCE BREAKDOWN:")
    for network, network_results in results_matrix.items():
        successes = sum(1 for r in network_results.values() if r.get('status') == 'success')
        no_results = sum(1 for r in network_results.values() if r.get('status') == 'no_results')
        no_pools = sum(1 for r in network_results.values() if r.get('status') == 'no_pools')
        errors = sum(1 for r in network_results.values() if r.get('status') == 'error')
        
        print(f"\n{network.upper()}:")
        print(f"  ✅ Successful: {successes}/24 ({(successes/24)*100:.1f}%)")
        print(f"  ❌ No results: {no_results}/24 (filtering issues)")
        print(f"  🚫 No pools: {no_pools}/24 (API issues)")
        print(f"  💥 Errors: {errors}/24 (system issues)")
        
        if successes > 0:
            print(f"  🎯 Working configurations:")
            for config_key, result in network_results.items():
                if result.get('status') == 'success':
                    print(f"    • {config_key}: {result['gems']} gems - {result['sample']}")
    
    print(f"\n🔍 PATTERN ANALYSIS:")
    
    api_issue_networks = []
    for network, network_results in results_matrix.items():
        no_pools_count = sum(1 for r in network_results.values() if r.get('status') == 'no_pools')
        error_count = sum(1 for r in network_results.values() if r.get('status') == 'error')
        if no_pools_count + error_count > 12:
            api_issue_networks.append(network)
    
    if api_issue_networks:
        print(f"  🚨 Networks with API issues: {', '.join(api_issue_networks)}")
    
    config_success_rates = {}
    ages = ['last_48', 'older_2_days']
    liquidities = ['10_50', '50_250', '250_1000', '1000_plus']
    mcaps = ['micro', 'small', 'mid']
    
    for age in ages:
        for liquidity in liquidities:
            for mcap in mcaps:
                config_key = f"{age}_{liquidity}_{mcap}"
                successes = sum(1 for network_results in results_matrix.values() 
                              if network_results.get(config_key, {}).get('status') == 'success')
                config_success_rates[config_key] = successes
    
    best_configs = sorted(config_success_rates.items(), key=lambda x: x[1], reverse=True)[:5]
    print(f"  🏆 Best performing configurations:")
    for config_key, success_count in best_configs:
        if success_count > 0:
            print(f"    • {config_key}: {success_count}/4 networks successful")

if __name__ == "__main__":
    print(f"🚀 Starting comprehensive gem research testing at {datetime.now()}")
    results = asyncio.run(test_complete_configuration_matrix())
    print(f"🏁 Testing completed at {datetime.now()}")
