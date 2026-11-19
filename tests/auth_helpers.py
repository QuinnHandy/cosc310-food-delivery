"""Signed-in test users for tests that call protected routes.

Import the `auth` fixture into a test module with
`from auth_helpers import auth  # noqa: F401  (pytest fixture)`, then pass
`headers=auth["owner1"]` to the test client.

The fixture copies the seed users into a subfolder of tmp_path, so it never touches data/ and
never collides with a test's own restaurants.json. Sessions are saved directly, because logging
in runs a slow password hash.
"""

import shutil
from datetime import datetime, timezone

import pytest

from app.api.dependencies import get_session_repository, get_user_repository
from app.core.config import PROJECT_ROOT
from app.main import app
from app.repositories.restaurant_repository import RestaurantRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import Session

# name -> user ID in data/users.json
SEEDED_USERS = {
    "admin": 1,
    "owner1": 2,  # owns restaurant 1
    "owner2": 3,  # owns restaurant 2
    "customer": 4,
    "deactivated": 6,  # a customer whose account is deactivated
}


@pytest.fixture
def auth(tmp_path):
    """Returns {name: Authorization headers} for each user in SEEDED_USERS."""
    data_dir = tmp_path / "auth_data"
    data_dir.mkdir()
    for name in ("restaurants.json", "users.json"):
        shutil.copy(PROJECT_ROOT / "data" / name, data_dir / name)
    users = UserRepository(
        data_dir / "users.json", RestaurantRepository(data_dir / "restaurants.json")
    )
    sessions = SessionRepository(data_dir / "sessions.json")
    app.dependency_overrides[get_user_repository] = lambda: users
    app.dependency_overrides[get_session_repository] = lambda: sessions

    headers = {}
    for name, user_id in SEEDED_USERS.items():
        token = f"test-token-{name}"
        sessions.add(
            Session(token=token, user_id=user_id, created_at=datetime.now(timezone.utc))
        )
        headers[name] = {"Authorization": f"Bearer {token}"}
    try:
        yield headers
    finally:
        app.dependency_overrides.pop(get_user_repository, None)
        app.dependency_overrides.pop(get_session_repository, None)
