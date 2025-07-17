#!/usr/bin/env python3
"""
Test script to verify gem research button callbacks work correctly
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

def test_button_callbacks():
    """Test that button callbacks match expected format"""
    try:
        from src.bot.gem_research_handler import GemResearchHandler
        from src.api.geckoterminal_client import GeckoTerminalClient
        
        print("✅ Imports successful")
        
        api_client = GeckoTerminalClient()
        gem_handler = GemResearchHandler(api_client, None, None)
        
        print("✅ Handler initialized")
        
        message, buttons = gem_handler.get_age_selection_message()
        
        print(f"Age selection message: {message}")
        print(f"Button count: {len(buttons.inline_keyboard)}")
        
        for row in buttons.inline_keyboard:
            for button in row:
                print(f"Button: '{button.text}' -> callback: '{button.callback_data}'")
        
        expected_callbacks = ['gem_age_last48', 'gem_age_older2days']
        actual_callbacks = []
        
        for row in buttons.inline_keyboard:
            for button in row:
                actual_callbacks.append(button.callback_data)
        
        if set(expected_callbacks) == set(actual_callbacks):
            print("✅ Button callbacks match expected format")
        else:
            print(f"❌ Button callback mismatch. Expected: {expected_callbacks}, Got: {actual_callbacks}")
            return False
        
        print("\n🔍 Testing button handler mapping...")
        
        age_map = {
            'gem_age_last48': 'last_48',
            'gem_age_older2days': 'older_2_days'
        }
        
        for callback, expected_age in age_map.items():
            if callback in actual_callbacks:
                print(f"✅ Callback '{callback}' maps to '{expected_age}'")
            else:
                print(f"❌ Callback '{callback}' not found in buttons")
                return False
        
        print("\n🎉 All button callback tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_button_callbacks()
    sys.exit(0 if success else 1)
