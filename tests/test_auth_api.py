import json
import shutil

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_session_repository, get_user_repository
from app.core.config import PROJECT_ROOT, settings
from app.main import app
from app.repositories.restaurant_repository import RestaurantRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository

COMMITTED_DATA = PROJECT_ROOT / "data"
PASSWORD = "Password123!"
ALICE = {"email": "alice@foodapp.test", "password": PASSWORD}


def copy_seed_data(target):
    for name in ("restaurants.json", "users.json"):
        shutil.copy(COMMITTED_DATA / name, target / name)


@pytest.fixture
def client(tmp_path):
    copy_seed_data(tmp_path)
    app.dependency_overrides[get_user_repository] = lambda: UserRepository(
        tmp_path / "users.json", RestaurantRepository(tmp_path / "restaurants.json")
    )
    app.dependency_overrides[get_session_repository] = lambda: SessionRepository(
        tmp_path / "sessions.json"
    )
    try:
        yield TestClient(app), tmp_path
    finally:
        app.dependency_overrides.pop(get_user_repository, None)
        app.dependency_overrides.pop(get_session_repository, None)


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_login_returns_token_user_and_role(client):
    test_client, tmp_path = client

    response = test_client.post("/auth/login", json=ALICE)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"token", "user_id", "role"}
    assert (body["user_id"], body["role"]) == (4, "customer")
    saved = json.loads((tmp_path / "sessions.json").read_text(encoding="utf-8"))
    assert [(s["token"], s["user_id"]) for s in saved] == [(body["token"], 4)]


# Failure case: wrong password and unknown email give the same 401.
def test_wrong_password_and_unknown_email_give_same_401(client):
    test_client, _ = client

    wrong_password = test_client.post("/auth/login", json={**ALICE, "password": "wrong"})
    unknown_email = test_client.post(
        "/auth/login", json={"email": "nobody@foodapp.test", "password": PASSWORD}
    )

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()
    assert wrong_password.headers["WWW-Authenticate"] == "Bearer"


# Failure case: the seeded deactivated customer.
def test_deactivated_account_gets_403(client):
    test_client, tmp_path = client

    response = test_client.post(
        "/auth/login", json={"email": "carol@foodapp.test", "password": PASSWORD}
    )

    assert response.status_code == 403
    assert not (tmp_path / "sessions.json").exists()


@pytest.mark.parametrize(
    "body",
    [{"email": "alice@foodapp.test"}, {"password": PASSWORD}, {**ALICE, "password": ""}],
    ids=["missing-password", "missing-email", "empty-password"],
)
def test_invalid_login_body_gets_422(client, body):
    test_client, _ = client

    assert test_client.post("/auth/login", json=body).status_code == 422


# Failure case: stored user records must not appear in the error sent to the caller.
def test_corrupt_user_file_gets_500_without_leaking_records(client):
    test_client, tmp_path = client
    user_file = tmp_path / "users.json"
    users = json.loads(user_file.read_text(encoding="utf-8"))
    del users[0]["name"]
    user_file.write_text(json.dumps(users), encoding="utf-8")

    response = test_client.post("/auth/login", json=ALICE)

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Could not access application data",
        "code": "data_access_error",
    }

def test_logout_ends_the_session(client):
    test_client, _ = client
    token = test_client.post("/auth/login", json=ALICE).json()["token"]

    first = test_client.post("/auth/logout", headers=bearer(token))
    second = test_client.post("/auth/logout", headers=bearer(token))

    assert first.status_code == 200
    assert first.json() == {"message": "Signed out"}
    assert second.status_code == 401
    assert second.headers["WWW-Authenticate"] == "Bearer"


# Failure cases: no usable bearer token in the request.
@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Basic abc123"}],
    ids=["no-header", "wrong-scheme"],
)
def test_logout_without_bearer_token_gets_401(client, headers):
    test_client, _ = client

    response = test_client.post("/auth/logout", headers=headers)

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Not authenticated",
        "code": "unauthorized",
    }
    assert response.headers["WWW-Authenticate"] == "Bearer"


# Failure case: an unreadable session file.
def test_corrupt_session_file_gets_500_on_logout(client):
    test_client, tmp_path = client
    (tmp_path / "sessions.json").write_text("{not json", encoding="utf-8")

    response = test_client.post("/auth/logout", headers=bearer("any-token"))

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Could not access application data",
        "code": "data_access_error",
    }

# The real providers (not the test overrides) read and write under settings.data_dir.
def test_default_providers_use_the_configured_data_folder(tmp_path, monkeypatch):
    copy_seed_data(tmp_path)
    monkeypatch.setattr(settings, "data_dir", tmp_path)

    token = TestClient(app).post("/auth/login", json=ALICE).json()["token"]

    assert SessionRepository(tmp_path / "sessions.json").get(token).user_id == 4


# Compares before and after, because a developer who ran the app may have a local sessions file.
def test_login_does_not_touch_committed_data_folder(client):
    test_client, tmp_path = client
    committed = COMMITTED_DATA / "sessions.json"
    before = committed.read_bytes() if committed.exists() else None

    assert test_client.post("/auth/login", json=ALICE).status_code == 200

    assert (tmp_path / "sessions.json").exists()
    assert (committed.read_bytes() if committed.exists() else None) == before
