"""
Shared test configuration and fixtures for BIGBALZ Bot tests
"""
import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

@pytest.fixture
def mock_api_client():
    """Mock API client for testing"""
    return AsyncMock()

@pytest.fixture
def mock_session_manager():
    """Mock session manager for testing"""
    return MagicMock()
