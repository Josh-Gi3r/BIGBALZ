#!/usr/bin/env python3
"""
Test the complete gem research flow to verify all components work together
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_complete_flow():
    """Test the complete gem research implementation"""
    try:
        from api.geckoterminal_client import GeckoTerminalClient
        from bot.gem_research_handler import GemResearchHandler, GemCriteria, GemResearchSession
        
        print("✅ All imports successful")
        
        # Initialize components
        api_client = GeckoTerminalClient()
        gem_handler = GemResearchHandler(api_client, None, None)
        
        print("✅ Components initialized")
        
        session = gem_handler.create_or_get_session(12345, 67890)
        print(f"✅ Session created: {session.step}")
        
        message, buttons = gem_handler.get_network_selection_message()
        print(f"✅ Network selection message: {len(message)} chars, {len(buttons.inline_keyboard)} button rows")
        
        message, buttons = gem_handler.get_age_selection_message()
        print(f"✅ Age selection message: {len(message)} chars, {len(buttons.inline_keyboard)} button rows")
        
        message, buttons = gem_handler.get_liquidity_selection_message()
        print(f"✅ Liquidity selection message: {len(message)} chars, {len(buttons.inline_keyboard)} button rows")
        
        message, buttons = gem_handler.get_mcap_selection_message()
        print(f"✅ Market cap selection message: {len(message)} chars, {len(buttons.inline_keyboard)} button rows")
        
        criteria = GemCriteria(network='solana', age='last_48', liquidity='50_250', mcap='micro')
        loading_msg = gem_handler.get_research_loading_message(criteria)
        print(f"✅ Loading message: {len(loading_msg)} chars")
        
        print("\n🔍 Testing API methods...")
        
        new_pools = await api_client.get_new_pools_paginated('solana', max_pools=10)
        print(f"✅ New pools paginated: {len(new_pools)} pools")
        
        if new_pools:
            contract = gem_handler._extract_contract_from_pool(new_pools[0])
            print(f"✅ Contract extraction: {contract}")
            
            filtered = gem_handler._filter_pools_by_liquidity(new_pools, '50_250')
            print(f"✅ Liquidity filtering: {len(filtered)} pools match criteria")
            
            classification = gem_handler._classify_gem_from_pool(new_pools[0], criteria)
            print(f"✅ Gem classification: {classification.name}")
            
            message, buttons = gem_handler.format_single_gem_result_from_pool(
                new_pools[0], criteria, 0, 1
            )
            print(f"✅ Result formatting: {len(message)} chars, {len(buttons.inline_keyboard)} button rows")
        
        print("\n🚀 Testing complete research execution...")
        session.criteria = criteria
        session.new_pools_list = new_pools[:5]  # Use first 5 for testing
        
        results = await gem_handler.execute_gem_research(session)
        print(f"✅ Research execution: {len(results)} gems found")
        
        if not results:
            message, buttons = gem_handler.get_no_gems_message('solana')
            print(f"✅ No gems message: {len(message)} chars, {len(buttons.inline_keyboard)} button rows")
        
        print("\n🎉 All tests passed! Gem research implementation is working.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_complete_flow())
