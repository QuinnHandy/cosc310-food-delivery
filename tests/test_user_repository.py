import json

import pytest
from pydantic import ValidationError

from app.core.config import PROJECT_ROOT
from app.core.security import verify_password
from app.repositories.restaurant_repository import (
    DataAccessError,
    RestaurantNotFoundError,
    RestaurantRepository,
)
from app.repositories.user_repository import (
    DuplicateEmailError,
    UserNotFoundError,
    UserRepository,
)
from app.schemas.user import User, UserCreateRecord, UserPublic, UserUpdate

RESTAURANTS = [
    {"id": 1, "name": "Test Pizza", "cuisine": "Italian"},
    {"id": 2, "name": "Test Sushi", "cuisine": "Japanese"},
]

# Repository tests never check passwords, so a fake hash string is enough here.
FAKE_HASH = "pbkdf2_sha256$1$00$00"


def entry(id, **overrides):
    base = {"id": id, "email": f"user{id}@test.com", "password_hash": FAKE_HASH,
            "role": "customer", "name": f"User {id}", "phone": "250-555-0100",
            "delivery_address": "1 Main St", "is_active": True, "restaurant_id": None}
    return {**base, **overrides}


def make_repo(tmp_path, users):
    restaurant_file = tmp_path / "restaurants.json"
    user_file = tmp_path / "users.json"
    restaurant_file.write_text(json.dumps(RESTAURANTS), encoding="utf-8")
    user_file.write_text(json.dumps(users), encoding="utf-8")
    return UserRepository(user_file, RestaurantRepository(restaurant_file)), user_file, restaurant_file


def new_user(**overrides):
    base = {"email": "new@test.com", "password_hash": FAKE_HASH, "role": "customer", "name": "New User"}
    return UserCreateRecord(**{**base, **overrides})


def test_list_all_loads_users(tmp_path):
    repo, _, _ = make_repo(tmp_path, [entry(1), entry(2, role="admin")])

    users = repo.list_all()

    assert [u.id for u in users] == [1, 2]
    assert users[1].role == "admin"


def test_get_returns_user(tmp_path):
    repo, _, _ = make_repo(tmp_path, [entry(1), entry(2)])

    assert repo.get(2).email == "user2@test.com"


# Failure case: unknown ID.
def test_get_unknown_id_raises(tmp_path):
    repo, _, _ = make_repo(tmp_path, [entry(1)])

    with pytest.raises(UserNotFoundError):
        repo.get(99)


def test_get_by_email_is_case_insensitive(tmp_path):
    repo, _, _ = make_repo(tmp_path, [entry(1, email="alice@test.com")])

    assert repo.get_by_email("Alice@TEST.com").id == 1
    assert repo.get_by_email("  alice@test.com ").id == 1


def test_get_by_email_unknown_returns_none(tmp_path):
    repo, _, _ = make_repo(tmp_path, [entry(1)])

    assert repo.get_by_email("nobody@test.com") is None


# New user IDs are max + 1, so a gap left by a missing ID is never reused.
def test_add_gets_next_id(tmp_path):
    repo, _, _ = make_repo(tmp_path, [entry(1), entry(5)])

    created = repo.add(new_user())

    assert created.id == 6
    assert [u.id for u in repo.list_all()] == [1, 5, 6]


# Data written survives a restart and the file still loads cleanly.
def test_added_user_loads_after_restart(tmp_path):
    repo, user_file, restaurant_file = make_repo(tmp_path, [entry(1)])
    repo.add(new_user(email="New@Test.com"))

    restarted = UserRepository(user_file, RestaurantRepository(restaurant_file))

    assert [u.email for u in restarted.list_all()] == ["user1@test.com", "new@test.com"]
    assert restarted.get(2).password_hash == FAKE_HASH
    assert list(tmp_path.glob("*.tmp")) == []


def test_add_owner_with_existing_restaurant(tmp_path):
    repo, _, _ = make_repo(tmp_path, [entry(1)])

    created = repo.add(new_user(email="owner@test.com", role="restaurant_owner", restaurant_id=2))

    assert (created.role, created.restaurant_id) == ("restaurant_owner", 2)


# Failure case: duplicate email in a different case, file unchanged.
def test_add_duplicate_email_raises_and_leaves_file_unchanged(tmp_path):
    repo, user_file, _ = make_repo(tmp_path, [entry(1, email="alice@test.com")])
    before = user_file.read_text(encoding="utf-8")

    with pytest.raises(DuplicateEmailError):
        repo.add(new_user(email="ALICE@test.com"))
    assert user_file.read_text(encoding="utf-8") == before


# Failure case: owner of a restaurant that does not exist, file unchanged.
def test_add_owner_of_unknown_restaurant_raises_and_leaves_file_unchanged(tmp_path):
    repo, user_file, _ = make_repo(tmp_path, [entry(1)])
    before = user_file.read_text(encoding="utf-8")

    with pytest.raises(RestaurantNotFoundError):
        repo.add(new_user(role="restaurant_owner", restaurant_id=99))
    assert user_file.read_text(encoding="utf-8") == before


# Partial update changes only the fields sent; ID, email and role stay the same.
def test_update_changes_only_sent_fields(tmp_path):
    repo, _, _ = make_repo(tmp_path, [entry(1, email="alice@test.com")])

    updated = repo.update(1, UserUpdate(phone="778-555-0199", is_active=False))

    assert (updated.id, updated.email, updated.role) == (1, "alice@test.com", "customer")
    assert updated.phone == "778-555-0199"
    assert updated.is_active is False
    assert updated.name == "User 1"
    assert repo.get(1) == updated


# Failure case: unknown ID.
def test_update_unknown_id_raises(tmp_path):
    repo, _, _ = make_repo(tmp_path, [entry(1)])

    with pytest.raises(UserNotFoundError):
        repo.update(99, UserUpdate(name="Nobody"))


# Failure case: invalid JSON.
def test_invalid_json_raises(tmp_path):
    repo, user_file, _ = make_repo(tmp_path, [])
    user_file.write_text("{not json", encoding="utf-8")

    with pytest.raises(DataAccessError):
        repo.list_all()


# Failure case: JSON that is not a list.
def test_non_list_file_raises(tmp_path):
    repo, user_file, _ = make_repo(tmp_path, [])
    user_file.write_text(json.dumps({"id": 1}), encoding="utf-8")

    with pytest.raises(DataAccessError):
        repo.list_all()


# Failure case: a record missing a required field.
def test_record_missing_required_field_raises(tmp_path):
    record = entry(1)
    del record["email"]
    repo, _, _ = make_repo(tmp_path, [record])

    with pytest.raises(DataAccessError):
        repo.list_all()


# Failure case: the file itself is missing.
def test_missing_file_raises(tmp_path):
    repo, user_file, _ = make_repo(tmp_path, [])
    user_file.unlink()

    with pytest.raises(DataAccessError):
        repo.list_all()


# Failure case: two users with the same email already in the file.
def test_duplicate_email_in_file_raises(tmp_path):
    repo, _, _ = make_repo(tmp_path, [entry(1, email="a@test.com"), entry(2, email="A@test.com")])

    with pytest.raises(DataAccessError):
        repo.list_all()


# Failure case: two users with the same ID already in the file.
def test_duplicate_id_in_file_raises(tmp_path):
    repo, _, _ = make_repo(tmp_path, [entry(1), entry(1, email="other@test.com")])

    with pytest.raises(DataAccessError):
        repo.list_all()


# Failure case: an owner points at a restaurant that is not in restaurants.json.
def test_owner_of_unknown_restaurant_in_file_raises(tmp_path):
    repo, _, _ = make_repo(tmp_path, [entry(1, role="restaurant_owner", restaurant_id=99)])

    with pytest.raises(DataAccessError):
        repo.list_all()


# Failure case: model rules for the owner-to-restaurant link.
def test_model_rejects_owner_without_restaurant_id():
    with pytest.raises(ValidationError):
        User(**entry(1, role="restaurant_owner", restaurant_id=None))


def test_model_rejects_customer_with_restaurant_id():
    with pytest.raises(ValidationError):
        User(**entry(1, role="customer", restaurant_id=1))


def test_model_rejects_bad_email():
    for bad in ["", "no-at-sign", "a@b", "a@@b.com", "a@b@c.com", "@b.com"]:
        with pytest.raises(ValidationError):
            User(**entry(1, email=bad))


def test_public_user_has_no_password_hash():
    assert "password_hash" not in UserPublic.model_fields
    public = UserPublic.model_validate(User(**entry(1)).model_dump())
    assert "password_hash" not in public.model_dump()


# Read-only: the committed seed data loads with the committed restaurants and every demo login works.
def test_committed_seed_data_loads_and_passwords_verify():
    repo = UserRepository(
        PROJECT_ROOT / "data" / "users.json",
        RestaurantRepository(PROJECT_ROOT / "data" / "restaurants.json"),
    )

    users = repo.list_all()

    assert [u.id for u in users] == [1, 2, 3, 4, 5, 6]
    assert [u.role for u in users].count("admin") == 1
    assert {u.restaurant_id for u in users if u.role == "restaurant_owner"} == {1, 2}
    assert [u.email for u in users if not u.is_active] == ["carol@foodapp.test"]
    assert all(verify_password("Password123!", u.password_hash) for u in users)
