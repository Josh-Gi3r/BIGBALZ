#!/usr/bin/env python3
"""Test ETH gem research session creation"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

async def test_eth_gem_research():
    from src.bot.gem_research_handler import GemResearchHandler
    from src.api.geckoterminal_client import GeckoTerminalClient
    from src.database.session_manager import SessionManager
    
    api_client = GeckoTerminalClient()
    session_manager = SessionManager()
    gem_handler = GemResearchHandler(api_client=api_client, session_manager=session_manager)
    
    chat_id, user_id = 12345, 67890
    session = gem_handler.create_or_get_session(chat_id, user_id)
    gem_handler.update_session_step(chat_id, user_id, 'age', network='eth')
    
    print('✅ ETH gem research session created successfully')
    print(f'✅ Network: {session.criteria.network}')
    print(f'✅ Step: {session.step}')

if __name__ == "__main__":
    asyncio.run(test_eth_gem_research())
