import json
from pathlib import Path

from pydantic import ValidationError

from app.repositories.restaurant_repository import DataAccessError, write_json_atomic
from app.schemas.auth import Session


class SessionRepository:
    """Reads and writes sign-in sessions in a JSON file. A missing file means no sessions yet."""

    def __init__(self, session_file: Path) -> None:
        self._session_file = Path(session_file)

    def _load(self) -> list[Session]:
        try:
            raw = self._session_file.read_text(encoding="utf-8")
        except FileNotFoundError:
            return []
        except OSError as exc:
            raise DataAccessError(
                f"Could not read session data file: {self._session_file}"
            ) from exc

        try:
            records = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise DataAccessError(
                f"Session data file is not valid JSON: {self._session_file}"
            ) from exc

        if not isinstance(records, list):
            raise DataAccessError(
                f"Session data file must contain a JSON list: {self._session_file}"
            )

        try:
            return [Session.model_validate(record) for record in records]
        except ValidationError as exc:
            raise DataAccessError(
                f"Session data file has a record that does not match the Session model: "
                f"{self._session_file}"
            ) from exc

    def _save(self, sessions: list[Session]) -> None:
        write_json_atomic(self._session_file, [s.model_dump(mode="json") for s in sessions])

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
