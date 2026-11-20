"""CustomerService rules (#83-#86), tested against a temporary copy of the seed data."""

import shutil

import pytest
from pydantic import ValidationError

from app.core.config import PROJECT_ROOT
from app.core.security import verify_password
from app.repositories.restaurant_repository import RestaurantRepository
from app.repositories.user_repository import UserRepository
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.schemas.user import UserRole
from app.services.customer_service import (
    CustomerAlreadyDeactivatedError,
    CustomerNotFoundError,
    CustomerService,
    EmailAlreadyRegisteredError,
)

ALICE_ID, CAROL_ID, OWNER_ID, ADMIN_ID = 4, 6, 2, 1


@pytest.fixture
def repo(tmp_path):
    for name in ("restaurants.json", "users.json"):
        shutil.copy(PROJECT_ROOT / "data" / name, tmp_path / name)
    return UserRepository(tmp_path / "users.json", RestaurantRepository(tmp_path / "restaurants.json"))


@pytest.fixture
def service(repo):
    return CustomerService(repo)


def new_customer(**overrides):
    data = {"name": "Dana", "email": "Dana@Example.com", "password": "longenough"}
    return CustomerCreate(**{**data, **overrides})


# ---- register (#83) ----

def test_register_creates_customer_with_hashed_password(service, repo):
    created = service.register(new_customer(phone="250-555-0199"))
    stored = repo.get(created.id)
    assert stored.role == UserRole.customer
    assert stored.email == "dana@example.com"
    assert stored.phone == "250-555-0199"
    assert stored.is_active is True
    assert stored.password_hash != "longenough"
    assert verify_password("longenough", stored.password_hash)


def test_register_assigns_next_id_and_it_survives_reload(service, tmp_path):
    first = service.register(new_customer())
    second = service.register(new_customer(email="eve@example.com"))
    assert second.id == first.id + 1
    reloaded = UserRepository(tmp_path / "users.json", RestaurantRepository(tmp_path / "restaurants.json"))
    assert reloaded.get(first.id).email == "dana@example.com"


def test_register_rejects_email_already_used_ignoring_case(service, repo):
    before = repo.list_all()
    with pytest.raises(EmailAlreadyRegisteredError):
        service.register(new_customer(email="ALICE@foodapp.test"))
    assert repo.list_all() == before  # nothing saved


@pytest.mark.parametrize(
    "overrides",
    [
        {"password": "short"},
        {"name": "   "},
        {"email": "not-an-email"},
        {"role": "admin"},  # the role cannot be chosen
    ],
)
def test_register_request_rejects_invalid_input(overrides):
    with pytest.raises(ValidationError):
        new_customer(**overrides)


# ---- view (#84) ----

def test_get_customer_returns_customer(service):
    assert service.get_customer(ALICE_ID).name == "Alice Smith"


@pytest.mark.parametrize("user_id", [999, OWNER_ID, ADMIN_ID])
def test_get_customer_unknown_or_not_a_customer_is_not_found(service, user_id):
    with pytest.raises(CustomerNotFoundError):
        service.get_customer(user_id)


# ---- update (#85) ----

def test_update_changes_only_sent_fields_and_persists(service, tmp_path):
    updated = service.update_customer(ALICE_ID, CustomerUpdate(delivery_address=" 9 New Rd "))
    assert updated.delivery_address == "9 New Rd"
    assert updated.name == "Alice Smith"
    reloaded = UserRepository(tmp_path / "users.json", RestaurantRepository(tmp_path / "restaurants.json"))
    assert reloaded.get(ALICE_ID).delivery_address == "9 New Rd"


def test_update_with_null_keeps_the_value(service):
    updated = service.update_customer(ALICE_ID, CustomerUpdate(name=None, phone="1"))
    assert updated.name == "Alice Smith"
    assert updated.phone == "1"


@pytest.mark.parametrize(
    "body", [{"name": ""}, {"delivery_address": "  "}, {"email": "x@y.com"}, {"is_active": False}, {"role": "admin"}]
)
def test_update_request_rejects_empty_values_and_protected_fields(body):
    with pytest.raises(ValidationError):
        CustomerUpdate(**body)


# ---- deactivate (#86) ----

def test_deactivate_keeps_the_account(service, repo):
    count = len(repo.list_all())
    result = service.deactivate_customer(ALICE_ID)
    assert result.is_active is False
    assert len(repo.list_all()) == count
    assert repo.get(ALICE_ID).is_active is False


def test_deactivate_twice_is_refused(service):
    with pytest.raises(CustomerAlreadyDeactivatedError):
        service.deactivate_customer(CAROL_ID)  # already deactivated in the seed data


def test_deactivate_owner_is_not_found(service):
    with pytest.raises(CustomerNotFoundError):
        service.deactivate_customer(OWNER_ID)
