#!/usr/bin/env python3
"""
Verify that algorithm extraction didn't break any imports
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_algorithm_imports():
    """Test that all algorithm modules can be imported"""
    try:
        from src.algorithms.moonshot_criteria import MOONSHOT_CRITERIA_LIST, TIER_CONFIG
        from src.algorithms.rug_detection import RUG_LIQUIDITY_DRAIN_CRITERIA, MAX_HISTORICAL_DATA_AGE
        from src.algorithms.balz_classification import BALZCategory, VOLUME_TIERS, LIQUIDITY_TIERS
        from src.algorithms.whale_confidence import WHALE_THRESHOLDS, CONFIDENCE_SCORING, RISK_LEVELS
        from src.algorithms.gem_risk_scoring import GEM_RISK_SCORING
        print("✅ All algorithm imports successful")
        return True
    except Exception as e:
        print(f"❌ Algorithm import error: {e}")
        return False

def test_core_imports():
    """Test that all core modules can still be imported"""
    try:
        from src.api.geckoterminal_client import GeckoTerminalClient
        from src.bot.telegram_handler import TelegramBotHandler
        from src.bot.button_handler import ButtonHandler
        from src.classification.reasoning_engine import ReasoningEngine
        from src.monitoring.background_monitor import BackgroundMonitor
        from src.database.session_manager import SessionManager
        from src.api.whale_tracker import WhaleTracker
        from src.bot.gem_research_handler import GemResearchHandler
        print("✅ All core imports successful")
        return True
    except Exception as e:
        print(f"❌ Core import error: {e}")
        return False

def test_algorithm_usage():
    """Test that algorithms are properly accessible"""
    try:
        from src.algorithms.moonshot_criteria import MOONSHOT_CRITERIA_LIST
        from src.algorithms.balz_classification import BALZCategory
        from src.algorithms.whale_confidence import WHALE_THRESHOLDS
        from src.algorithms.gem_risk_scoring import GEM_RISK_SCORING
        
        assert len(MOONSHOT_CRITERIA_LIST) == 3
        assert MOONSHOT_CRITERIA_LIST[0]['tier'] == 'POTENTIAL 100X'
        
        assert BALZCategory.TRASH.value == 'TRASH'
        assert BALZCategory.OPPORTUNITY.value == 'OPPORTUNITY'
        
        assert 'mega_whale' in WHALE_THRESHOLDS
        assert WHALE_THRESHOLDS['mega_whale'] == 5.0
        
        assert 'max_score' in GEM_RISK_SCORING
        assert GEM_RISK_SCORING['max_score'] == 10
        
        print("✅ All algorithm usage tests passed")
        return True
    except Exception as e:
        print(f"❌ Algorithm usage error: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Verifying algorithm extraction...")
    
    success = True
    success &= test_algorithm_imports()
    success &= test_core_imports()
    success &= test_algorithm_usage()
    
    if success:
        print("\n🎉 Algorithm extraction verification PASSED!")
        print("All secret sauce successfully extracted to algorithm files.")
    else:
        print("\n❌ Algorithm extraction verification FAILED!")
        print("Some imports or functionality may be broken.")
    
    sys.exit(0 if success else 1)
