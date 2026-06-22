"""
Session Manager for Cognitive Agents
====================================
Tracks and manages active CognitiveAgent instances in-memory to preserve
conversation history across requests.
"""

import logging
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from backend.app.agent.cognitive_agent import create_agent, CognitiveAgent

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages active cognitive agent sessions, ensuring thread-safe operations.
    """

    def __init__(self):
        # Stores: { session_id: { "agent": CognitiveAgent, "role": str, "region": Optional[str], "last_accessed": datetime } }
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()

    def get_or_create_agent(
        self, session_id: str, role: str, region: Optional[str]
    ) -> CognitiveAgent:
        """
        Retrieves an existing agent session if the role matches,
        or creates a new agent instance.
        """
        with self.lock:
            now = datetime.now(timezone.utc)
            if session_id in self.sessions:
                session = self.sessions[session_id]
                # If the role matches, reuse the existing agent and update last accessed time
                if session["role"] == role:
                    session["last_accessed"] = now
                    logger.info(f"Reusing existing session for ID={session_id}, role={role}")
                    return session["agent"]
                else:
                    logger.info(
                        f"Role changed for session ID={session_id} ({session['role']} -> {role}). Recreating agent."
                    )
                    # Implicitly destroyed by overwriting below

            # Create new agent and session
            logger.info(f"Creating new session for ID={session_id}, role={role}, region={region}")
            agent = create_agent(role=role, region=region, verbose=True)
            self.sessions[session_id] = {
                "agent": agent,
                "role": role,
                "region": region,
                "last_accessed": now,
            }
            return agent

    def destroy_session(self, session_id: str):
        """
        Removes an agent session from memory.
        """
        with self.lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                logger.info(f"Destroyed session ID={session_id}")

    def cleanup_stale_sessions(self, max_age_minutes: int = 30):
        """
        Identifies and removes sessions that have not been accessed for longer than max_age_minutes.
        """
        with self.lock:
            now = datetime.now(timezone.utc)
            stale_keys = []
            for session_id, session in self.sessions.items():
                age_minutes = (now - session["last_accessed"]).total_seconds() / 60.0
                if age_minutes > max_age_minutes:
                    stale_keys.append(session_id)

            for session_id in stale_keys:
                del self.sessions[session_id]
                logger.info(
                    f"Cleaned up stale session ID={session_id} (inactive for {age_minutes:.1f} minutes)"
                )


# Global singleton instance
session_manager = SessionManager()
