from pathlib import Path

from app.repositories.json_store import JsonStore
from app.schemas.auth import Session


class SessionRepository:
    """Reads and writes sign-in sessions in a JSON file. A missing file means no sessions yet."""

    def __init__(self, session_file: Path) -> None:
        # Validation details would quote stored tokens, so they are left out of errors.
        self._store = JsonStore(
            session_file, Session, "session", missing_ok=True, hide_record_details=True
        )

    def _load(self) -> list[Session]:
        return self._store.load()

    def _save(self, sessions: list[Session]) -> None:
        self._store.save(sessions)

    def get(self, token: str) -> Session | None:
        for session in self._load():
            if session.token == token:
                return session
        return None

    def add(self, session: Session) -> Session:
        self._save([*self._load(), session])
        return session

    def delete(self, token: str) -> bool:
        """Remove a session. Returns True if it existed."""
        sessions = self._load()
        remaining = [s for s in sessions if s.token != token]
        if len(remaining) == len(sessions):
            return False
        self._save(remaining)
        return True
