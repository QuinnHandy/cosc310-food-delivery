"""CartService rules (#89-#92) on a temporary copy of the seed data, without HTTP.

Seed menu: restaurant 1 has item 1 ($15.50), item 2 ($7.00) and item 3 (unavailable);
restaurant 2 starts at item 4.
"""

import json
import shutil
from decimal import Decimal

import pytest

from app.core.config import PROJECT_ROOT
from app.repositories.cart_repository import CartRepository
from app.repositories.menu_repository import MenuItemNotFoundError, MenuRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.repositories.user_repository import UserRepository
from app.schemas.menu import MenuItemUpdate
from app.services.customer_service import CustomerService
from app.services.menu_service import MenuService
from app.services.cart_service import (
    CartItemNotInCartError,
    CartService,
    CustomerNotAllowedError,
    DifferentRestaurantError,
    MenuItemUnavailableError,
    QuantityLimitError,
)

FEE = Decimal("4.99")


@pytest.fixture
def env(tmp_path):
    for name in ("restaurants.json", "menus.json", "users.json"):
        shutil.copy(PROJECT_ROOT / "data" / name, tmp_path / name)
    restaurants = RestaurantRepository(tmp_path / "restaurants.json")
    menus = MenuRepository(tmp_path / "menus.json", restaurants)
    users = UserRepository(tmp_path / "users.json", restaurants)
    carts = CartRepository(tmp_path / "carts.json")
    return {
        "service": CartService(carts, MenuService(menus), CustomerService(users), FEE),
        "menus": menus,
        "carts": carts,
        "alice": users.get(4),
        "bob": users.get(5),
        "carol": users.get(6),  # deactivated
        "owner": users.get(2),
        "cart_file": tmp_path / "carts.json",
        "menu_file": tmp_path / "menus.json",
    }


def stored(env):
    return env["cart_file"].read_text() if env["cart_file"].exists() else None


# ---- get (#89) ----

def test_get_creates_one_empty_cart_and_reuses_it(env):
    first = env["service"].get_cart(env["alice"])
    second = env["service"].get_cart(env["alice"])
    assert first.id == second.id
    assert first.items == [] and first.total == 0 and first.delivery_fee == 0
    assert len(env["carts"].list_all()) == 1


def test_each_customer_gets_their_own_cart(env):
    a = env["service"].get_cart(env["alice"])
    b = env["service"].get_cart(env["bob"])
    assert a.id != b.id and b.customer_id == 5


@pytest.mark.parametrize("who", ["carol", "owner"])
def test_deactivated_customers_and_other_roles_have_no_cart(env, who):
    with pytest.raises(CustomerNotAllowedError):
        env["service"].get_cart(env[who])
    with pytest.raises(CustomerNotAllowedError):
        env["service"].add_item(env[who], 1, 1)
    assert stored(env) is None  # nothing created


# ---- add (#90) ----

def test_add_item_prices_from_the_menu(env):
    cart = env["service"].add_item(env["alice"], 1, 2)
    assert cart.restaurant_id == 1
    line = cart.items[0]
    assert (line.name, line.unit_price, line.quantity, line.line_total) == ("Kung Pao Chicken", 15.5, 2, 31.0)
    assert (cart.subtotal, cart.delivery_fee, cart.total) == (31.0, 4.99, 35.99)


def test_adding_the_same_item_again_increases_quantity(env):
    env["service"].add_item(env["alice"], 1, 2)
    cart = env["service"].add_item(env["alice"], 1, 3)
    assert len(cart.items) == 1 and cart.items[0].quantity == 5


def test_quantity_cannot_go_above_20_in_total(env):
    env["service"].add_item(env["alice"], 1, 18)
    before = stored(env)
    with pytest.raises(QuantityLimitError):
        env["service"].add_item(env["alice"], 1, 3)
    assert stored(env) == before


def test_unknown_item_is_refused(env):
    with pytest.raises(MenuItemNotFoundError):
        env["service"].add_item(env["alice"], 999, 1)


def test_unavailable_item_is_refused(env):
    env["service"].add_item(env["alice"], 1, 1)
    before = stored(env)
    with pytest.raises(MenuItemUnavailableError):
        env["service"].add_item(env["alice"], 3, 1)  # Beef Chow Mein, unavailable
    assert stored(env) == before


def test_deactivated_item_is_refused(env):
    items = json.loads(env["menu_file"].read_text())
    items[1]["is_active"] = False  # item 2
    env["menu_file"].write_text(json.dumps(items))
    with pytest.raises(MenuItemUnavailableError):
        env["service"].add_item(env["alice"], 2, 1)


def test_items_from_another_restaurant_are_refused(env):
    env["service"].add_item(env["alice"], 1, 1)
    before = stored(env)
    with pytest.raises(DifferentRestaurantError):
        env["service"].add_item(env["alice"], 4, 1)  # restaurant 2
    assert stored(env) == before
    assert [l.menu_item_id for l in env["service"].get_cart(env["alice"]).items] == [1]


# ---- change, remove, clear (#91) ----

def test_set_quantity(env):
    env["service"].add_item(env["alice"], 1, 1)
    cart = env["service"].set_quantity(env["alice"], 1, 4)
    assert cart.items[0].quantity == 4 and cart.subtotal == 62.0


def test_change_or_remove_item_not_in_cart_is_refused(env):
    env["service"].add_item(env["alice"], 1, 1)
    with pytest.raises(CartItemNotInCartError):
        env["service"].set_quantity(env["alice"], 2, 1)
    with pytest.raises(CartItemNotInCartError):
        env["service"].remove_item(env["alice"], 2)


def test_removing_last_item_frees_the_restaurant(env):
    env["service"].add_item(env["alice"], 1, 1)
    env["service"].add_item(env["alice"], 2, 1)
    assert env["service"].remove_item(env["alice"], 1).restaurant_id == 1
    cart = env["service"].remove_item(env["alice"], 2)
    assert cart.restaurant_id is None and cart.total == 0
    assert env["service"].add_item(env["alice"], 4, 1).restaurant_id == 2


def test_clear_keeps_the_cart_id_and_resets_restaurant(env):
    cart_id = env["service"].add_item(env["alice"], 1, 2).id
    cleared = env["service"].clear(env["alice"])
    assert cleared.id == cart_id and cleared.items == [] and cleared.restaurant_id is None
    assert env["service"].add_item(env["alice"], 4, 1).restaurant_id == 2


# ---- totals use current prices (#92) ----

def test_a_price_change_shows_in_the_next_cart(env):
    env["service"].add_item(env["alice"], 1, 2)
    env["menus"].update_item(1, 1, MenuItemUpdate(price=16.25))
    cart = env["service"].get_cart(env["alice"])
    assert cart.items[0].unit_price == 16.25
    assert cart.total == 37.49  # 32.50 + 4.99


def test_item_that_became_unavailable_is_flagged(env):
    env["service"].add_item(env["alice"], 1, 1)
    env["menus"].update_item(1, 1, MenuItemUpdate(is_available=False))
    assert env["service"].get_cart(env["alice"]).items[0].is_available is False


def test_cart_survives_a_restart(env, tmp_path):
    cart_id = env["service"].add_item(env["alice"], 2, 3).id
    restaurants = RestaurantRepository(tmp_path / "restaurants.json")
    fresh = CartService(
        CartRepository(tmp_path / "carts.json"),
        MenuService(MenuRepository(tmp_path / "menus.json", restaurants)),
        CustomerService(UserRepository(tmp_path / "users.json", restaurants)),
        FEE,
    )
    cart = fresh.get_cart(env["alice"])
    assert cart.id == cart_id and cart.items[0].quantity == 3
