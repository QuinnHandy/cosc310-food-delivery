import json

import pytest

from app.core.security import hash_password
from app.repositories.restaurant_repository import RestaurantRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserRole
from app.services.auth_service import (
    AccountDeactivatedError,
    AuthService,
    InvalidCredentialsError,
)

PASSWORD = "Password123!"
PASSWORD_HASH = hash_password(PASSWORD)
RESTAURANTS = [{"id": 1, "name": "Test Pizza", "cuisine": "Italian"}]


def entry(id, **overrides):
    base = {"id": id, "email": f"user{id}@test.com", "password_hash": PASSWORD_HASH,
            "role": "customer", "name": f"User {id}", "phone": "", "delivery_address": "",
            "is_active": True, "restaurant_id": None}
    return {**base, **overrides}


def make_service(tmp_path, users):
    restaurant_file = tmp_path / "restaurants.json"
    user_file = tmp_path / "users.json"
    session_file = tmp_path / "sessions.json"
    restaurant_file.write_text(json.dumps(RESTAURANTS), encoding="utf-8")
    user_file.write_text(json.dumps(users), encoding="utf-8")
    service = AuthService(
        UserRepository(user_file, RestaurantRepository(restaurant_file)),
        SessionRepository(session_file),
    )
    return service, session_file


# A session is saved with the user's ID and still exists after a restart.
def test_login_saves_session_that_survives_restart(tmp_path):
    service, session_file = make_service(tmp_path, [entry(1), entry(2)])

    result = service.login("user2@test.com", PASSWORD)

    assert result.token
    assert (result.user_id, result.role) == (2, UserRole.customer)
    saved = SessionRepository(session_file).get(result.token)
    assert saved.user_id == 2
    assert saved.created_at.tzinfo is not None


def test_login_email_is_case_insensitive(tmp_path):
    service, _ = make_service(tmp_path, [entry(1)])

    assert service.login("USER1@Test.com", PASSWORD).user_id == 1


def test_two_logins_give_different_tokens(tmp_path):
    service, session_file = make_service(tmp_path, [entry(1)])

    first = service.login("user1@test.com", PASSWORD)
    second = service.login("user1@test.com", PASSWORD)

    assert first.token != second.token
    sessions = SessionRepository(session_file)
    assert sessions.get(first.token) is not None
    assert sessions.get(second.token) is not None


# Failure case: both errors read the same, so a caller cannot tell which emails exist.
def test_wrong_password_and_unknown_email_give_same_error(tmp_path):
    service, session_file = make_service(tmp_path, [entry(1)])

    with pytest.raises(InvalidCredentialsError) as wrong_password:
        service.login("user1@test.com", "not-the-password")
    with pytest.raises(InvalidCredentialsError) as unknown_email:
        service.login("nobody@test.com", PASSWORD)

    assert str(wrong_password.value) == str(unknown_email.value) == "Invalid email or password"
    assert not session_file.exists()


# Failure case: the right password for a deactivated account creates no session.
def test_deactivated_user_with_right_password_raises(tmp_path):
    service, session_file = make_service(tmp_path, [entry(1, is_active=False)])

    with pytest.raises(AccountDeactivatedError):
        service.login("user1@test.com", PASSWORD)
    assert not session_file.exists()


# Failure case: without the right password, a deactivated account looks like any other.
def test_deactivated_user_with_wrong_password_gets_invalid_credentials(tmp_path):
    service, _ = make_service(tmp_path, [entry(1, is_active=False)])

    with pytest.raises(InvalidCredentialsError):
        service.login("user1@test.com", "not-the-password")


def test_logout_deletes_only_that_session(tmp_path):
    service, session_file = make_service(tmp_path, [entry(1)])
    first = service.login("user1@test.com", PASSWORD)
    second = service.login("user1@test.com", PASSWORD)

    service.logout(first.token)

    sessions = SessionRepository(session_file)
    assert sessions.get(first.token) is None
    assert sessions.get(second.token) is not None


# Failure case: a token that is not a current session.
def test_logout_unknown_token_raises(tmp_path):
    service, _ = make_service(tmp_path, [entry(1)])

    with pytest.raises(InvalidCredentialsError):
        service.logout("not-a-real-token")
