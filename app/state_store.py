"""
State store for session persistence.
Handles saving and loading sessions to/from disk.
"""
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.models import Session, FlowState

logger = logging.getLogger(__name__)


class StateStore:
    """Manages session persistence to disk."""

    def __init__(self, sessions_dir: Optional[str] = None):
        self.sessions_dir = Path(sessions_dir or os.getenv("SESSIONS_DIR", "./sessions"))
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"StateStore initialized with directory: {self.sessions_dir}")

    def _generate_session_id(self, storyline: str = "") -> str:
        """Generate a unique session ID with timestamp and slug."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create slug from storyline (first few words)
        slug = "session"
        if storyline:
            # Clean and truncate storyline for slug
            words = re.sub(r"[^a-zA-Z0-9\s]", "", storyline).split()[:3]
            if words:
                slug = "_".join(w.lower() for w in words)
                slug = slug[:30]  # Limit length

        return f"{timestamp}_{slug}"

    def _get_session_path(self, session_id: str) -> Path:
        """Get the file path for a session."""
        return self.sessions_dir / f"{session_id}.json"

    def create_session(self, storyline: str = "") -> Session:
        """Create a new session."""
        session_id = self._generate_session_id(storyline)
        session = Session(session_id=session_id)
        self.save_session(session)
        logger.info(f"Created new session: {session_id}")
        return session

    def save_session(self, session: Session) -> None:
        """Save session to disk."""
        session.update_timestamp()
        path = self._get_session_path(session.session_id)

        # Convert to dict and handle datetime serialization
        data = session.model_dump()
        data["created_at"] = session.created_at.isoformat()
        data["updated_at"] = session.updated_at.isoformat()

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

        logger.debug(f"Saved session: {session.session_id}")

    def load_session(self, session_id: str) -> Optional[Session]:
        """Load a session from disk."""
        path = self._get_session_path(session_id)

        if not path.exists():
            logger.warning(f"Session not found: {session_id}")
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Parse datetime strings back to datetime objects
            if isinstance(data.get("created_at"), str):
                data["created_at"] = datetime.fromisoformat(data["created_at"])
            if isinstance(data.get("updated_at"), str):
                data["updated_at"] = datetime.fromisoformat(data["updated_at"])

            session = Session(**data)
            logger.info(f"Loaded session: {session_id}")
            return session

        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None

    def list_sessions(self) -> list[dict]:
        """List all available sessions."""
        sessions = []

        for path in self.sessions_dir.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                sessions.append({
                    "session_id": data.get("session_id"),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                    "state": data.get("current_state"),
                    "slide_count": len(data.get("current_outline", {}).get("slides", []))
                    if data.get("current_outline")
                    else 0,
                })
            except Exception as e:
                logger.warning(f"Failed to read session file {path}: {e}")

        # Sort by updated_at descending
        sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return sessions

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        path = self._get_session_path(session_id)

        if path.exists():
            path.unlink()
            logger.info(f"Deleted session: {session_id}")
            return True

        logger.warning(f"Session not found for deletion: {session_id}")
        return False

    def session_exists(self, session_id: str) -> bool:
        """Check if a session exists."""
        return self._get_session_path(session_id).exists()


class LogStore:
    """Manages logging of LLM calls for audit."""

    def __init__(self, logs_dir: Optional[str] = None):
        self.logs_dir = Path(logs_dir or os.getenv("LOGS_DIR", "./logs"))
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def _get_log_path(self, session_id: str) -> Path:
        """Get the log file path for a session."""
        return self.logs_dir / f"{session_id}_llm_calls.jsonl"

    def log_llm_call(
        self,
        session_id: str,
        step: str,
        request: dict,
        response: dict,
        redact_keys: list[str] = None,
    ) -> None:
        """Log an LLM call to the session's log file."""
        redact_keys = redact_keys or []

        # Redact sensitive data
        def redact(obj, keys):
            if isinstance(obj, dict):
                return {
                    k: "[REDACTED]" if k in keys else redact(v, keys)
                    for k, v in obj.items()
                }
            elif isinstance(obj, list):
                return [redact(item, keys) for item in obj]
            return obj

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "request": redact(request, redact_keys),
            "response": redact(response, redact_keys),
        }

        path = self._get_log_path(session_id)

        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, default=str) + "\n")

        logger.debug(f"Logged LLM call for session {session_id}, step: {step}")

    def get_logs(self, session_id: str) -> list[dict]:
        """Retrieve all logs for a session."""
        path = self._get_log_path(session_id)

        if not path.exists():
            return []

        logs = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    logs.append(json.loads(line))

        return logs
