import json
from datetime import datetime, timezone

import pytest

from app.repositories.restaurant_repository import DataAccessError
from app.repositories.session_repository import SessionRepository
from app.schemas.auth import Session

CREATED_AT = datetime(2026, 11, 18, 12, 30, tzinfo=timezone.utc)


def session(token="token-1", user_id=1):
    return Session(token=token, user_id=user_id, created_at=CREATED_AT)


def make_repo(tmp_path):
    session_file = tmp_path / "sessions.json"
    return SessionRepository(session_file), session_file


# Sessions are created at runtime, so a missing file just means nobody is signed in.
def test_missing_file_counts_as_empty(tmp_path):
    repo, session_file = make_repo(tmp_path)

    assert repo.get("token-1") is None
    assert repo.delete("token-1") is False
    assert not session_file.exists()


# Data written survives a restart, including the timestamp.
def test_added_session_loads_after_restart(tmp_path):
    repo, session_file = make_repo(tmp_path)
    repo.add(session())

    restarted = SessionRepository(session_file)

    assert restarted.get("token-1") == session()
    assert list(tmp_path.glob("*.tmp")) == []


def test_get_unknown_token_returns_none(tmp_path):
    repo, _ = make_repo(tmp_path)
    repo.add(session())

    assert repo.get("other-token") is None


def test_delete_removes_only_that_session(tmp_path):
    repo, _ = make_repo(tmp_path)
    repo.add(session("token-1"))
    repo.add(session("token-2", user_id=2))

    assert repo.delete("token-1") is True

    assert repo.get("token-1") is None
    assert repo.get("token-2").user_id == 2
    assert list(tmp_path.glob("*.tmp")) == []


# Failure case: deleting an unknown token reports False and leaves the file unchanged.
def test_delete_unknown_token_leaves_file_unchanged(tmp_path):
    repo, session_file = make_repo(tmp_path)
    repo.add(session())
    before = session_file.read_text(encoding="utf-8")

    assert repo.delete("other-token") is False
    assert session_file.read_text(encoding="utf-8") == before


# Failure cases: a file that exists but cannot be understood is an error, not "no sessions".
@pytest.mark.parametrize(
    "content",
    ["{not json", json.dumps({"token": "token-1"}), json.dumps([{"token": "token-1"}])],
    ids=["invalid-json", "not-a-list", "bad-record"],
)
def test_unreadable_content_raises(tmp_path, content):
    repo, session_file = make_repo(tmp_path)
    session_file.write_text(content, encoding="utf-8")

    with pytest.raises(DataAccessError):
        repo.get("token-1")
