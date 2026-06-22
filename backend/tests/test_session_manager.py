import pytest
from datetime import datetime, timezone, timedelta
from backend.app.agent.session_manager import SessionManager
from backend.app.agent.cognitive_agent import CognitiveAgent


def test_session_manager_get_or_create():
    """Test session creation and caching logic."""
    manager = SessionManager()

    # 1. Create a session
    agent1 = manager.get_or_create_agent("session_123", "viewer", None)
    assert agent1 is not None
    assert isinstance(agent1, CognitiveAgent)

    # 2. Get the same session -> should return cached agent
    agent2 = manager.get_or_create_agent("session_123", "viewer", None)
    assert agent1 is agent2  # Must be the exact same object reference

    # 3. Request same session but different role -> should recreate
    agent3 = manager.get_or_create_agent("session_123", "admin", None)
    assert agent3 is not agent1
    assert manager.sessions["session_123"]["role"] == "admin"


def test_session_manager_destroy():
    """Test manual session destruction."""
    manager = SessionManager()
    manager.get_or_create_agent("session_123", "viewer", None)
    assert "session_123" in manager.sessions

    manager.destroy_session("session_123")
    assert "session_123" not in manager.sessions


def test_session_manager_cleanup():
    """Test automated cleanup of stale sessions."""
    manager = SessionManager()

    # Create two sessions
    manager.get_or_create_agent("session_active", "viewer", None)
    manager.get_or_create_agent("session_stale", "viewer", None)

    # Artificially age "session_stale"
    manager.sessions["session_stale"]["last_accessed"] = datetime.now(
        timezone.utc
    ) - timedelta(minutes=40)

    # Run cleanup with 30-minute threshold
    manager.cleanup_stale_sessions(max_age_minutes=30)

    # "session_stale" should be deleted, "session_active" must remain
    assert "session_stale" not in manager.sessions
    assert "session_active" in manager.sessions
