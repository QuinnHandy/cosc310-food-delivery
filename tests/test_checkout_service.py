"""CheckoutService (#94) on a temporary copy of the seed data, without HTTP.

Seed data: Alice (user 4) is an active customer with an address; Carol (6) is deactivated.
Restaurant 1 (Golden Dragon) has item 1 ($15.50), item 2 ($7.00) and item 3 (unavailable).
"""

import json
import shutil
from decimal import Decimal

import pytest

from app.core.config import PROJECT_ROOT
from app.repositories.cart_repository import CartRepository
from app.repositories.json_store import DataAccessError
from app.repositories.menu_repository import MenuRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.repositories.user_repository import UserRepository
from app.schemas.cart import Cart, CartLine, CartStatus
from app.schemas.menu import MenuItemUpdate
from app.schemas.user import UserUpdate
from app.services.cart_service import CartService
from app.services.checkout_service import (
    CartChangedError,
    CheckoutNotAllowedError,
    CheckoutService,
    DeliveryAddressRequiredError,
    EmptyCartError,
)
from app.services.customer_service import CustomerService
from app.services.menu_service import MenuService

FEE = Decimal("4.99")


class FailingOrderRepository:
    """Stands in for OrderRepository when saving an order fails."""

    def add(self, draft):
        raise DataAccessError("disk full")


@pytest.fixture
def env(tmp_path):
    for name in ("restaurants.json", "menus.json", "users.json"):
        shutil.copy(PROJECT_ROOT / "data" / name, tmp_path / name)
    restaurants = RestaurantRepository(tmp_path / "restaurants.json")
    menus = MenuRepository(tmp_path / "menus.json", restaurants)
    users = UserRepository(tmp_path / "users.json", restaurants)
    carts = CartRepository(tmp_path / "carts.json")
    orders = OrderRepository(tmp_path / "orders.json")
    customer_service = CustomerService(users)
    menu_service = MenuService(menus)
    cart_service = CartService(carts, menu_service, customer_service, FEE)

    def make_service(order_repository=orders):
        return CheckoutService(
            customer_service, cart_service, menu_service, restaurants, order_repository, FEE
        )

    return {
        "checkout": make_service(),
        "make_service": make_service,
        "cart_service": cart_service,
        "menus": menus,
        "users": users,
        "carts": carts,
        "orders": orders,
        "alice": users.get(4),
        "carol": users.get(6),
        "owner": users.get(2),
        "cart_file": tmp_path / "carts.json",
        "order_file": tmp_path / "orders.json",
    }


def stored_carts(env):
    return env["cart_file"].read_text() if env["cart_file"].exists() else None


def stored_orders(env):
    return env["order_file"].read_text() if env["order_file"].exists() else None


def fill_cart(env, *pairs):
    for item_id, quantity in pairs:
        env["cart_service"].add_item(env["alice"], item_id, quantity)


# ---- happy path ----

def test_checkout_creates_an_order_snapshot(env):
    fill_cart(env, (1, 2), (2, 1))
    order = env["checkout"].checkout(env["alice"])

    assert order.id == 1 and order.customer_id == 4
    assert order.restaurant_id == 1 and order.restaurant_name == "Golden Dragon"
    assert order.delivery_address == "123 Main St, Kelowna, BC"
    assert [(l.menu_item_id, l.name, l.unit_price, l.quantity, l.line_total) for l in order.items] == [
        (1, "Kung Pao Chicken", 15.5, 2, 31.0),
        (2, "Vegetable Spring Rolls", 7.0, 1, 7.0),
    ]
    assert (order.subtotal, order.delivery_fee, order.total) == (38.0, 4.99, 42.99)
    assert env["orders"].get_by_id(order.id) == order  # it was really saved


def test_cart_is_checked_out_and_next_cart_is_new_and_empty(env):
    fill_cart(env, (1, 1))
    old_cart_id = env["cart_service"].get_cart(env["alice"]).id
    env["checkout"].checkout(env["alice"])

    assert env["carts"].get_by_id(old_cart_id).status == CartStatus.checked_out
    new_cart = env["cart_service"].get_cart(env["alice"])
    assert new_cart.id != old_cart_id
    assert new_cart.items == [] and new_cart.status == CartStatus.active


def test_second_checkout_of_the_same_cart_is_refused(env):
    fill_cart(env, (1, 1))
    env["checkout"].checkout(env["alice"])
    with pytest.raises(EmptyCartError):
        env["checkout"].checkout(env["alice"])
    assert len(env["orders"].list_all()) == 1


# ---- prices come from the current menu ----

def test_price_changed_before_checkout_uses_the_new_price(env):
    fill_cart(env, (1, 2))
    env["menus"].update_item(1, 1, MenuItemUpdate(price=20.0))
    order = env["checkout"].checkout(env["alice"])
    assert order.items[0].unit_price == 20.0
    assert order.items[0].line_total == 40.0
    assert (order.subtotal, order.total) == (40.0, 44.99)


def test_later_menu_changes_do_not_change_the_order(env):
    fill_cart(env, (1, 1))
    order = env["checkout"].checkout(env["alice"])
    env["menus"].update_item(1, 1, MenuItemUpdate(price=99.0, name="Renamed"))
    saved = env["orders"].get_by_id(order.id)
    assert saved.items[0].unit_price == 15.5 and saved.items[0].name == "Kung Pao Chicken"


# ---- refusals write nothing ----

def test_item_made_unavailable_is_refused_naming_the_item_and_writes_nothing(env):
    fill_cart(env, (1, 1), (2, 1))
    env["menus"].update_item(1, 2, MenuItemUpdate(is_available=False))
    carts_before = stored_carts(env)

    with pytest.raises(CartChangedError, match="Vegetable Spring Rolls"):
        env["checkout"].checkout(env["alice"])

    assert env["orders"].list_all() == []
    assert stored_orders(env) in (None, "[]")
    assert stored_carts(env) == carts_before
    assert env["carts"].get_active_for_customer(4) is not None


def test_deactivated_item_is_refused(env):
    fill_cart(env, (1, 1))
    items = json.loads((env["menus"]._store.path).read_text())
    for item in items:
        if item["id"] == 1:
            item["is_active"] = False
    env["menus"]._store.path.write_text(json.dumps(items))
    with pytest.raises(CartChangedError, match="Kung Pao Chicken"):
        env["checkout"].checkout(env["alice"])
    assert env["orders"].list_all() == []


def test_item_that_no_longer_exists_is_refused(env):
    fill_cart(env, (1, 1))
    items = [i for i in json.loads(env["menus"]._store.path.read_text()) if i["id"] != 1]
    env["menus"]._store.path.write_text(json.dumps(items))
    with pytest.raises(CartChangedError, match="no longer exists"):
        env["checkout"].checkout(env["alice"])
    assert env["orders"].list_all() == []


def test_restaurant_that_no_longer_exists_is_refused(env, tmp_path):
    fill_cart(env, (1, 1))
    cart = env["carts"].get_active_for_customer(4)
    env["carts"].save(cart.model_copy(update={"restaurant_id": 99}))
    with pytest.raises(CartChangedError, match="restaurant"):
        env["checkout"].checkout(env["alice"])
    assert env["orders"].list_all() == []


def test_deactivated_customer_is_refused(env):
    with pytest.raises(CheckoutNotAllowedError):
        env["checkout"].checkout(env["carol"])
    assert env["orders"].list_all() == []


def test_customer_deactivated_after_sign_in_is_refused(env):
    fill_cart(env, (1, 1))
    stale_user = env["alice"]  # still looks active, as the token's user did at sign-in
    env["users"].update(4, UserUpdate(is_active=False))
    with pytest.raises(CheckoutNotAllowedError):
        env["checkout"].checkout(stale_user)
    assert env["orders"].list_all() == []


def test_other_roles_are_refused(env):
    with pytest.raises(CheckoutNotAllowedError):
        env["checkout"].checkout(env["owner"])


def test_customer_without_a_delivery_address_is_refused(env):
    fill_cart(env, (1, 1))
    env["users"].update(4, UserUpdate(delivery_address=""))
    with pytest.raises(DeliveryAddressRequiredError):
        env["checkout"].checkout(env["alice"])
    assert env["orders"].list_all() == []


def test_empty_cart_is_refused(env):
    with pytest.raises(EmptyCartError):
        env["checkout"].checkout(env["alice"])
    assert env["orders"].list_all() == []


def test_checkout_with_no_cart_at_all_writes_nothing(env):
    with pytest.raises(EmptyCartError):
        env["checkout"].checkout(env["alice"])
    assert stored_carts(env) is None  # no cart file was created
    assert stored_orders(env) is None  # and no order file


def test_a_cart_with_a_removed_line_is_empty_again(env):
    fill_cart(env, (1, 1))
    env["cart_service"].remove_item(env["alice"], 1)
    with pytest.raises(EmptyCartError):
        env["checkout"].checkout(env["alice"])


# ---- atomicity ----

def test_failed_order_save_leaves_the_cart_untouched(env):
    fill_cart(env, (1, 2))
    carts_before = stored_carts(env)
    service = env["make_service"](FailingOrderRepository())

    with pytest.raises(DataAccessError):
        service.checkout(env["alice"])

    assert stored_carts(env) == carts_before
    cart = env["carts"].get_active_for_customer(4)
    assert cart is not None and cart.status == CartStatus.active
    assert cart.items == [CartLine(menu_item_id=1, quantity=2)]
    assert stored_orders(env) in (None, "[]")


def test_customers_only_get_their_own_orders(env):
    fill_cart(env, (1, 1))
    env["checkout"].checkout(env["alice"])
    assert len(env["orders"].list_for_customer(4)) == 1
    assert env["orders"].list_for_customer(5) == []
