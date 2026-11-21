"""The ordering rules shared by the cart and checkout live in one place each (#109).

- "Is this an active customer?"  -> CustomerService.require_active_customer
- "Can this item be ordered?"    -> MenuService.get_orderable_item / MenuService.is_orderable

These tests check the shared methods directly, then check that the cart and checkout refuse
exactly the same bad states with the same message, so the two can't drift apart again.

Seed data: Alice (user 4) is an active customer, Carol (6) is deactivated, user 2 is an owner.
Restaurant 1 has item 1 ($15.50), item 2 ($7.00) and item 3 (unavailable).
"""

import inspect
import shutil
from decimal import Decimal

import pytest

from app.core.config import PROJECT_ROOT
from app.repositories.cart_repository import CartRepository
from app.repositories.menu_repository import MenuItemNotFoundError, MenuRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.repositories.user_repository import UserRepository
from app.schemas.menu import MenuItemUpdate
from app.schemas.user import UserUpdate
from app.services import cart_service as cart_module
from app.services import checkout_service as checkout_module
from app.services.cart_service import CartService
from app.services.checkout_service import CartChangedError, CheckoutNotAllowedError, CheckoutService
from app.services.customer_service import CustomerNotAllowedError, CustomerService
from app.services.menu_service import MenuItemUnavailableError, MenuService

FEE = Decimal("4.99")


@pytest.fixture
def env(tmp_path):
    for name in ("restaurants.json", "menus.json", "users.json"):
        shutil.copy(PROJECT_ROOT / "data" / name, tmp_path / name)
    restaurants = RestaurantRepository(tmp_path / "restaurants.json")
    menus = MenuRepository(tmp_path / "menus.json", restaurants)
    users = UserRepository(tmp_path / "users.json", restaurants)
    orders = OrderRepository(tmp_path / "orders.json")
    customers = CustomerService(users)
    menu_service = MenuService(menus)
    cart = CartService(CartRepository(tmp_path / "carts.json"), menu_service, customers, FEE)
    checkout = CheckoutService(customers, cart, menu_service, restaurants, orders, FEE)
    return {
        "customers": customers,
        "menu_service": menu_service,
        "menus": menus,
        "users": users,
        "orders": orders,
        "cart": cart,
        "checkout": checkout,
        "alice": users.get(4),
        "carol": users.get(6),
        "owner": users.get(2),
    }


# ---- CustomerService.require_active_customer ----

def test_active_customer_is_allowed_and_the_stored_record_is_returned(env):
    assert env["customers"].require_active_customer(env["alice"]).id == 4


@pytest.mark.parametrize(
    "who, message",
    [("carol", "This account has been deactivated"), ("owner", "Only customers")],
)
def test_inactive_or_non_customers_are_refused(env, who, message):
    with pytest.raises(CustomerNotAllowedError, match=message):
        env["customers"].require_active_customer(env[who])


def test_customer_deactivated_after_sign_in_is_refused(env):
    stale_alice = env["alice"]  # looks active, like the User object a request started with
    env["users"].update(4, UserUpdate(is_active=False))
    with pytest.raises(CustomerNotAllowedError, match="deactivated"):
        env["customers"].require_active_customer(stale_alice)


def test_unknown_customer_is_refused(env):
    ghost = env["alice"].model_copy(update={"id": 999})
    with pytest.raises(CustomerNotAllowedError, match="not found"):
        env["customers"].require_active_customer(ghost)


# ---- MenuService.get_orderable_item / is_orderable ----

@pytest.mark.parametrize(
    "is_active, is_available, expected",
    [(True, True, True), (True, False, False), (False, True, False), (False, False, False)],
)
def test_is_orderable_needs_active_and_available(env, is_active, is_available, expected):
    item = env["menus"].get_item(1).model_copy(
        update={"is_active": is_active, "is_available": is_available}
    )
    assert MenuService.is_orderable(item) is expected


def test_orderable_item_is_returned(env):
    assert env["menu_service"].get_orderable_item(1).name == "Kung Pao Chicken"


def test_unavailable_item_is_refused(env):
    with pytest.raises(MenuItemUnavailableError, match="not available to order"):
        env["menu_service"].get_orderable_item(3)


def test_deactivated_item_is_refused(env):
    env["menus"].deactivate_item(1, 1)
    with pytest.raises(MenuItemUnavailableError, match="not available to order"):
        env["menu_service"].get_orderable_item(1)


def test_unknown_item_is_not_found(env):
    with pytest.raises(MenuItemNotFoundError):
        env["menu_service"].get_orderable_item(999)


# ---- the cart and checkout refuse the same states with the same message ----

def make_unavailable(env):
    env["menus"].update_item(1, 2, MenuItemUpdate(is_available=False))


def make_deactivated(env):
    env["menus"].deactivate_item(1, 2)


@pytest.mark.parametrize("break_item", [make_unavailable, make_deactivated])
def test_cart_and_checkout_refuse_the_same_item_states(env, break_item):
    env["cart"].add_item(env["alice"], 2, 1)  # in the cart while it was still orderable
    break_item(env)

    with pytest.raises(MenuItemUnavailableError) as from_cart:
        env["cart"].add_item(env["alice"], 2, 1)
    with pytest.raises(CartChangedError) as from_checkout:
        env["checkout"].checkout(env["alice"])

    assert str(from_cart.value) == str(from_checkout.value)
    assert env["orders"].list_all() == []


def deactivate_alice_after_sign_in(env):
    stale = env["alice"]
    env["users"].update(4, UserUpdate(is_active=False))
    return stale


def owner(env):
    return env["owner"]


@pytest.mark.parametrize("get_user", [deactivate_alice_after_sign_in, owner])
def test_cart_and_checkout_refuse_the_same_customers(env, get_user):
    user = get_user(env)

    with pytest.raises(CustomerNotAllowedError) as from_cart:
        env["cart"].get_cart(user)
    with pytest.raises(CheckoutNotAllowedError) as from_checkout:
        env["checkout"].checkout(user)

    assert str(from_cart.value) == str(from_checkout.value)


def test_regression_cart_refuses_a_customer_deactivated_after_sign_in(env):
    """Regression for #109: before the shared rule, CartService only looked at the User object
    it was given, while checkout re-read the account. A customer deactivated after signing in
    could still add to their cart through the service (checkout already refused them)."""
    stale = deactivate_alice_after_sign_in(env)
    with pytest.raises(CustomerNotAllowedError, match="deactivated"):
        env["cart"].add_item(stale, 1, 1)


def test_cart_and_checkout_no_longer_contain_their_own_copies_of_the_rules():
    for module in (cart_module, checkout_module):
        source = inspect.getsource(module)
        assert "is_available" not in source.replace("is_available=", "")
        assert ".is_active" not in source
        assert "UserRole.customer" not in source
