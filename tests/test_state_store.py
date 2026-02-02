"""
Tests for state store.
"""
import os
import pytest
import tempfile
import shutil
from pathlib import Path

from app.state_store import StateStore, LogStore
from app.models import Session, FlowState, StorylineInput


class TestStateStore:
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp)

    @pytest.fixture
    def store(self, temp_dir):
        """Create a StateStore with temporary directory."""
        return StateStore(sessions_dir=temp_dir)

    def test_create_session(self, store):
        session = store.create_session("Test storyline")
        assert session.session_id is not None
        assert "test" in session.session_id.lower()
        assert session.current_state == FlowState.INIT

    def test_save_and_load_session(self, store):
        # Create and modify session
        session = store.create_session("Test")
        session.current_state = FlowState.PARTNER_REVIEW
        session.storyline_iterations = 2
        session.storyline_input = StorylineInput(storyline="My storyline")

        # Save
        store.save_session(session)

        # Load
        loaded = store.load_session(session.session_id)
        assert loaded is not None
        assert loaded.session_id == session.session_id
        assert loaded.current_state == FlowState.PARTNER_REVIEW
        assert loaded.storyline_iterations == 2
        assert loaded.storyline_input.storyline == "My storyline"

    def test_list_sessions(self, store):
        # Create multiple sessions
        store.create_session("First")
        store.create_session("Second")
        store.create_session("Third")

        sessions = store.list_sessions()
        assert len(sessions) == 3

    def test_delete_session(self, store):
        session = store.create_session("To delete")
        assert store.session_exists(session.session_id)

        result = store.delete_session(session.session_id)
        assert result is True
        assert not store.session_exists(session.session_id)

    def test_delete_nonexistent_session(self, store):
        result = store.delete_session("nonexistent")
        assert result is False

    def test_load_nonexistent_session(self, store):
        result = store.load_session("nonexistent")
        assert result is None

    def test_session_id_generation(self, store):
        # Test with storyline
        session1 = store.create_session("Digital Transformation Strategy")
        assert "digital" in session1.session_id.lower()

        # Test without storyline
        session2 = store.create_session("")
        assert "session" in session2.session_id.lower()

    def test_session_ordering(self, store):
        # Create sessions with slight delay
        import time
        store.create_session("First")
        time.sleep(0.01)
        store.create_session("Second")
        time.sleep(0.01)
        session3 = store.create_session("Third")

        # List should be ordered by updated_at descending
        sessions = store.list_sessions()
        assert sessions[0]["session_id"] == session3.session_id


class TestLogStore:
    @pytest.fixture
    def temp_dir(self):
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp)

    @pytest.fixture
    def log_store(self, temp_dir):
        return LogStore(logs_dir=temp_dir)

    def test_log_llm_call(self, log_store):
        log_store.log_llm_call(
            session_id="test_session",
            step="partner_review",
            request={"storyline": "Test", "api_key": "secret"},
            response={"review": {"overall": "Good"}},
            redact_keys=["api_key"],
        )

        logs = log_store.get_logs("test_session")
        assert len(logs) == 1
        assert logs[0]["step"] == "partner_review"
        assert logs[0]["request"]["api_key"] == "[REDACTED]"

    def test_multiple_logs(self, log_store):
        for i in range(5):
            log_store.log_llm_call(
                session_id="test_session",
                step=f"step_{i}",
                request={},
                response={},
            )

        logs = log_store.get_logs("test_session")
        assert len(logs) == 5

    def test_get_logs_empty(self, log_store):
        logs = log_store.get_logs("nonexistent")
        assert logs == []
