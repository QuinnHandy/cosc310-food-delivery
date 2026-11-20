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
from app.services.customer_service import CustomerNotFoundError, CustomerService
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
        "service": OrderService(orders, CustomerService(users)),
        "checkout": checkout,
        "carts": carts,
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


# ---- listing orders (#96) ----

def place_order(env, user, item_id=1, quantity=1):
    env["carts"].add_item(user, item_id, quantity)
    return env["checkout"].checkout(user)


def test_my_orders_are_only_mine_and_newest_first(env):
    second = place_order(env, env["alice"], 2, 1)  # Alice's second order
    place_order(env, env["bob"], 1, 1)  # Bob's order must not appear
    orders = env["service"].list_my_orders(env["alice"])
    assert [o.id for o in orders] == [second.id, env["order"].id]
    assert all(o.customer_id == 4 for o in orders)


def test_customer_with_no_orders_gets_an_empty_list(env):
    assert env["service"].list_my_orders(env["bob"]) == []


@pytest.mark.parametrize("who", ["owner", "admin", "carol"])
def test_only_active_customers_list_their_own_orders(env, who):
    with pytest.raises(OrderNotAllowedError):
        env["service"].list_my_orders(env[who])


def test_admin_lists_any_customers_orders(env):
    orders = env["service"].list_orders_for_customer(env["admin"], 4)
    assert [o.id for o in orders] == [env["order"].id]
    assert env["service"].list_orders_for_customer(env["admin"], 5) == []


@pytest.mark.parametrize("who", ["alice", "bob", "owner"])
def test_non_admins_cannot_list_another_customers_orders(env, who):
    with pytest.raises(OrderNotAllowedError):
        env["service"].list_orders_for_customer(env[who], 4)


@pytest.mark.parametrize("customer_id", [99, 1, 2])  # unknown, the admin, an owner
def test_unknown_customer_raises_not_found(env, customer_id):
    with pytest.raises(CustomerNotFoundError):
        env["service"].list_orders_for_customer(env["admin"], customer_id)
