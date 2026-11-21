"""Tests for get_current_user and require_role.

They run against a small throwaway FastAPI app with test-only routes, so the real app's routes
and OpenAPI schema are not touched. All data lives in tmp_path.
"""

import json
import shutil
from datetime import datetime, timezone

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies import (
    get_current_user,
    get_session_repository,
    get_user_repository,
    require_role,
)
from app.core.config import PROJECT_ROOT
from app.core.errors import DomainError
from app.main import domain_error_handler
from app.repositories.restaurant_repository import RestaurantRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import Session
from app.schemas.user import User, UserUpdate

COMMITTED_DATA = PROJECT_ROOT / "data"

# Seeded users (data/users.json): 1 admin, 2 owner of restaurant 1, 4 customer, 6 deactivated.
ADMIN, OWNER, CUSTOMER, DEACTIVATED = 1, 2, 4, 6


def create_test_app() -> FastAPI:
    test_app = FastAPI()

    test_app.add_exception_handler(DomainError, domain_error_handler)

    @test_app.get("/whoami")
    def whoami(user: User = Depends(get_current_user)):
        return {"id": user.id, "role": user.role}

    @test_app.get("/admin-only")
    def admin_only(user: User = Depends(require_role("admin"))):
        return {"id": user.id}

    @test_app.get("/staff")
    def staff(user: User = Depends(require_role("restaurant_owner", "admin"))):
        return {"id": user.id}


    return test_app


@pytest.fixture
def env(tmp_path):
    for name in ("restaurants.json", "users.json"):
        shutil.copy(COMMITTED_DATA / name, tmp_path / name)
    users = UserRepository(
        tmp_path / "users.json", RestaurantRepository(tmp_path / "restaurants.json")
    )
    sessions = SessionRepository(tmp_path / "sessions.json")

    test_app = create_test_app()
    test_app.dependency_overrides[get_user_repository] = lambda: users
    test_app.dependency_overrides[get_session_repository] = lambda: sessions

    def sign_in(user_id: int) -> dict:
        """Saves a session for the user directly (no slow password hashing) and returns headers."""
        token = f"token-for-user-{user_id}"
        sessions.add(
            Session(token=token, user_id=user_id, created_at=datetime.now(timezone.utc))
        )
        return {"Authorization": f"Bearer {token}"}

    return TestClient(test_app), users, sessions, sign_in, tmp_path


# --- get_current_user ---------------------------------------------------------------------


def test_valid_token_returns_the_user(env):
    client, _, _, sign_in, _ = env

    response = client.get("/whoami", headers=sign_in(CUSTOMER))

    assert response.status_code == 200
    assert response.json() == {"id": CUSTOMER, "role": "customer"}


# Failure case: no Authorization header at all.
def test_no_header_gives_401_with_www_authenticate(env):
    client, *_ = env

    response = client.get("/whoami")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


# Failure case: a token that is not in sessions.json.
def test_unknown_token_gives_401(env):
    client, *_ = env

    response = client.get("/whoami", headers={"Authorization": "Bearer not-a-real-token"})

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "header",
    ["Basic dXNlcjpwYXNz", "Bearer", "Bearer ", "token-for-user-4", ""],
    ids=["basic-scheme", "no-token", "blank-token", "no-scheme", "empty"],
)
# Failure case: malformed headers.
def test_malformed_header_gives_401(env, header):
    client, _, _, sign_in, _ = env
    sign_in(CUSTOMER)  # a real session exists, so only the header format is wrong

    response = client.get("/whoami", headers={"Authorization": header})

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


# Failure case: the account is deactivated (the seeded Carol), so the session is refused.
def test_deactivated_user_gives_403(env):
    client, _, _, sign_in, _ = env

    response = client.get("/whoami", headers=sign_in(DEACTIVATED))

    assert response.status_code == 403
    assert response.json() == {
        "detail": "This account has been deactivated",
        "code": "forbidden",
    }
    assert "WWW-Authenticate" not in response.headers


# Failure case: a user who signed in and was deactivated afterwards is refused straight away.
def test_user_deactivated_after_sign_in_gives_403(env):
    client, users, _, sign_in, _ = env
    headers = sign_in(CUSTOMER)
    assert client.get("/whoami", headers=headers).status_code == 200

    users.update(CUSTOMER, UserUpdate(is_active=False))

    assert client.get("/whoami", headers=headers).status_code == 403


# Failure case: the session points at a user who is not in users.json any more.
def test_session_for_a_missing_user_gives_401(env):
    client, _, _, sign_in, _ = env

    response = client.get("/whoami", headers=sign_in(999))

    assert response.status_code == 401


# Failure case: a signed-out token stops working.
def test_deleted_session_gives_401(env):
    client, _, sessions, sign_in, _ = env
    headers = sign_in(CUSTOMER)
    sessions.delete(f"token-for-user-{CUSTOMER}")

    assert client.get("/whoami", headers=headers).status_code == 401


# Failure case: unreadable user data is a 500 that does not leak what is stored.
def test_unreadable_user_data_gives_500_without_details(env):
    client, _, _, sign_in, tmp_path = env
    headers = sign_in(CUSTOMER)
    users_file = tmp_path / "users.json"
    broken = json.loads(users_file.read_text(encoding="utf-8"))
    broken[0]["role"] = "not-a-role"  # the error text would quote this record
    users_file.write_text(json.dumps(broken), encoding="utf-8")

    response = client.get("/whoami", headers=headers)

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Could not access application data",
        "code": "data_access_error",
    }

# --- require_role -------------------------------------------------------------------------


def test_allowed_role_gives_200(env):
    client, _, _, sign_in, _ = env

    assert client.get("/admin-only", headers=sign_in(ADMIN)).status_code == 200
    assert client.get("/staff", headers=sign_in(OWNER)).status_code == 200
    assert client.get("/staff", headers=sign_in(ADMIN)).status_code == 200


# Failure case: signed in, but with the wrong role.
@pytest.mark.parametrize(
    "path, user_id",
    [("/admin-only", CUSTOMER), ("/admin-only", OWNER), ("/staff", CUSTOMER)],
)
def test_wrong_role_gives_403(env, path, user_id):
    client, _, _, sign_in, _ = env

    response = client.get(path, headers=sign_in(user_id))

    assert response.status_code == 403
    assert response.json() == {
        "detail": "You do not have permission to do this",
        "code": "forbidden",
    }
    assert "WWW-Authenticate" not in response.headers


# Failure case: a role check does not skip the sign-in checks.
def test_require_role_without_token_gives_401(env):
    client, *_ = env

    assert client.get("/admin-only").status_code == 401
    assert client.get("/staff", headers={"Authorization": "Bearer nope"}).status_code == 401


# Failure case: a deactivated admin-role account is refused with 403 before the role matters.
def test_require_role_with_deactivated_user_gives_403(env):
    client, users, _, sign_in, _ = env
    headers = sign_in(ADMIN)
    users.update(ADMIN, UserUpdate(is_active=False))

    assert client.get("/admin-only", headers=headers).status_code == 403


def test_require_role_accepts_enum_values_and_rejects_typos():
    from app.schemas.user import UserRole

    require_role(UserRole.admin)  # does not raise
    with pytest.raises(ValueError):
        require_role("adimn")
    with pytest.raises(ValueError):
        require_role()


# --- OpenAPI ------------------------------------------------------------------------------


def test_protected_routes_show_the_bearer_scheme_in_openapi(env):
    client, *_ = env

    schema = client.get("/openapi.json").json()

    assert schema["components"]["securitySchemes"] == {
        "HTTPBearer": {
            "type": "http",
            "scheme": "bearer",
            "description": "Token from POST /auth/login",
        }
    }
    for path in ("/whoami", "/admin-only", "/staff"):
        assert schema["paths"][path]["get"]["security"] == [{"HTTPBearer": []}]
