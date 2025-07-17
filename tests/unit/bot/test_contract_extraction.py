#!/usr/bin/env python3
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from api.geckoterminal_client import GeckoTerminalClient
from bot.gem_research_handler import GemResearchHandler

async def test_contract_extraction():
    """Test the contract address extraction from pool data"""
    client = GeckoTerminalClient()
    handler = GemResearchHandler(client, None, None)
    
    print("Testing contract address extraction...")
    
    pools = await client.get_new_pools('solana', limit=3)
    if pools:
        for i, pool in enumerate(pools):
            contract = handler._extract_contract_from_pool(pool)
            attrs = pool.get('attributes', {})
            name = attrs.get('name', 'Unknown')
            print(f"Pool {i+1}: {name} -> Contract: {contract}")
    else:
        print("No pools found")

if __name__ == "__main__":
    asyncio.run(test_contract_extraction())
