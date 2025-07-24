#!/usr/bin/env python3
"""Test script for new troll response system"""

import sys
sys.path.append('src')

from ai.conversation_handler import ConversationHandler

def test_troll_responses():
    """Test that troll responses are short and direct"""
    print("Testing new troll response system...")
    
    try:
        conv_handler = ConversationHandler(openai_api_key="test_key")
        user_id = 12345
        
        insults = [
            "you suck",
            "you're stupid", 
            "stupid bot",
            "you're trash",
            "shut up"
        ]
        
        print("Testing troll responses:")
        for insult in insults:
            is_troll = conv_handler._is_insult_or_troll(insult)
            if is_troll:
                response = conv_handler._get_troll_response(user_id)
                print(f"  '{insult}' -> '{response}' (length: {len(response)} chars)")
            else:
                print(f"  '{insult}' -> Not detected as troll")
        
        print("\nTesting memory cooldowns:")
        for i in range(5):
            response = conv_handler._get_troll_response(user_id)
            print(f"  Response {i+1}: '{response}'")
        
        print("\n✅ Troll response system working!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_troll_responses()
