"""Pytest configuration and fixtures for UniTools SDK tests."""

import pytest


@pytest.fixture
def sample_context():
    """Provide a sample context dictionary for testing."""
    return {
        "user_id": "test_user_001",
        "session_id": "session_123",
        "permissions": ["read", "write"],
    }
