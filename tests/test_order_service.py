"""OrderService (#95): who may view an order, without HTTP.

Seed data: Alice (user 4) and Bob (5) are active customers, Carol (6) is deactivated,
user 2 is a restaurant owner and user 1 is the admin.
"""

import shutil
from decimal import Decimal

import pytest

from app.core.config import PROJECT_ROOT
from app.repositories.cart_repository import CartRepository
from app.repositories.menu_repository import MenuRepository
from app.repositories.order_repository import OrderNotFoundError, OrderRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.repositories.user_repository import UserRepository
from app.schemas.menu import MenuItemUpdate
from app.services.cart_service import CartService
from app.services.checkout_service import CheckoutService
from app.services.customer_service import CustomerService
from app.services.order_service import OrderNotAllowedError, OrderService

FEE = Decimal("4.99")


@pytest.fixture
def env(tmp_path):
    for name in ("restaurants.json", "menus.json", "users.json"):
        shutil.copy(PROJECT_ROOT / "data" / name, tmp_path / name)
    restaurants = RestaurantRepository(tmp_path / "restaurants.json")
    menus = MenuRepository(tmp_path / "menus.json", restaurants)
    users = UserRepository(tmp_path / "users.json", restaurants)
    orders = OrderRepository(tmp_path / "orders.json")
    carts = CartService(CartRepository(tmp_path / "carts.json"), menus, FEE)
    checkout = CheckoutService(CustomerService(users), carts, menus, restaurants, orders, FEE)

    alice = users.get(4)
    carts.add_item(alice, 1, 2)
    order = checkout.checkout(alice)  # order 1: Alice, 2 x Kung Pao Chicken at $15.50
    return {
        "service": OrderService(orders),
        "menus": menus,
        "users": users,
        "order": order,
        "alice": alice,
        "bob": users.get(5),
        "carol": users.get(6),
        "owner": users.get(2),
        "admin": users.get(1),
    }


def test_customer_views_their_own_order_with_snapshot_and_totals(env):
    order = env["service"].get_order(env["alice"], env["order"].id)
    assert order == env["order"]
    assert [(l.name, l.unit_price, l.quantity, l.line_total) for l in order.items] == [
        ("Kung Pao Chicken", 15.5, 2, 31.0)
    ]
    assert (order.subtotal, order.delivery_fee, order.total) == (31.0, 4.99, 35.99)


def test_another_customers_order_is_refused(env):
    with pytest.raises(OrderNotAllowedError):
        env["service"].get_order(env["bob"], env["order"].id)


def test_admin_can_view_any_order(env):
    assert env["service"].get_order(env["admin"], env["order"].id).customer_id == 4


@pytest.mark.parametrize("who", ["owner", "carol"])
def test_restaurant_owner_and_deactivated_customer_are_refused(env, who):
    with pytest.raises(OrderNotAllowedError):
        env["service"].get_order(env[who], env["order"].id)


def test_unknown_order_raises_not_found(env):
    with pytest.raises(OrderNotFoundError):
        env["service"].get_order(env["alice"], 99)
    with pytest.raises(OrderNotFoundError):
        env["service"].get_order(env["admin"], 99)


def test_changing_the_menu_afterwards_does_not_change_the_order(env):
    env["menus"].update_item(1, 1, MenuItemUpdate(price=99.0, name="Renamed Dish"))
    order = env["service"].get_order(env["alice"], env["order"].id)
    assert order.items[0].name == "Kung Pao Chicken"
    assert order.items[0].unit_price == 15.5
    assert (order.subtotal, order.total) == (31.0, 35.99)
