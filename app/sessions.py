from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class Session:
    id: str
    created_at: float
    updated_at: float
    turns: list[dict[str, str]] = field(default_factory=list)
    agent_context_id: str | None = None


class SessionStore:
    def __init__(self, ttl_seconds: int = 7200, max_turns: int = 20) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_turns = max_turns
        self._items: dict[str, Session] = {}
        self._lock = Lock()

    def _prune(self) -> None:
        cutoff = time.time() - self.ttl_seconds
        for session_id in [key for key, value in self._items.items() if value.updated_at < cutoff]:
            self._items.pop(session_id, None)

    def create(self) -> Session:
        with self._lock:
            self._prune()
            now = time.time()
            session = Session(f"session-{uuid.uuid4().hex[:12]}", now, now)
            self._items[session.id] = session
            return session

    def get(self, session_id: str) -> Session | None:
        with self._lock:
            self._prune()
            session = self._items.get(session_id)
            if session:
                session.updated_at = time.time()
            return session

    def append_turn(self, session_id: str, user: str, assistant: str) -> Session:
        with self._lock:
            session = self._items[session_id]
            session.turns.extend(({"role": "user", "content": user}, {"role": "assistant", "content": assistant}))
            session.turns = session.turns[-self.max_turns * 2 :]
            session.updated_at = time.time()
            return session

    def delete(self, session_id: str) -> Session | None:
        with self._lock:
            return self._items.pop(session_id, None)

    def count(self) -> int:
        with self._lock:
            self._prune()
            return len(self._items)
