"""A whole-app test setup on a temporary copy of data/, for tests that cross subsystems.

Import the fixture with `from app_data_helpers import app_data  # noqa: F401  (pytest fixture)`.

`app_data` copies every committed data/*.json file into tmp_path and points
`settings.data_dir` there, so every repository the app builds (users, sessions, restaurants,
menus, carts, ...) reads and writes the copy. Nothing in data/ is touched. It also saves a
session for each seeded user, so tests can call protected endpoints without the slow login.

Not a conftest.py on purpose, so it doesn't collide with #100 (shared fixtures), which can
absorb it.
"""

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import PROJECT_ROOT, settings
from app.main import app
from app.repositories.session_repository import SessionRepository
from app.schemas.auth import Session

# name -> user ID in data/users.json (every seeded password is "Password123!")
SEEDED_USERS = {
    "admin": 1,
    "owner1": 2,  # owns restaurant 1 (Golden Dragon)
    "owner2": 3,  # owns restaurant 2 (Spice Garden)
    "customer": 4,  # Alice
    "customer2": 5,  # Bob
    "deactivated": 6,  # Carol, a deactivated customer
}


@dataclass
class AppData:
    client: TestClient
    data_dir: Path
    headers: dict[str, dict[str, str]]  # name -> Authorization header


@pytest.fixture
def app_data(tmp_path, monkeypatch) -> AppData:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for path in (PROJECT_ROOT / "data").glob("*.json"):
        if path.name != "sessions.json":
            shutil.copy(path, data_dir / path.name)
    monkeypatch.setattr(settings, "data_dir", data_dir)

    sessions = SessionRepository(data_dir / "sessions.json")
    headers = {}
    for name, user_id in SEEDED_USERS.items():
        token = f"test-token-{name}"
        sessions.add(Session(token=token, user_id=user_id, created_at=datetime.now(timezone.utc)))
        headers[name] = {"Authorization": f"Bearer {token}"}
    return AppData(TestClient(app), data_dir, headers)
