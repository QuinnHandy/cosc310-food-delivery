"""CartRepository (#88): storage only, tested without the API."""

import json

import pytest

from app.repositories.cart_repository import CartNotFoundError, CartRepository
from app.repositories.restaurant_repository import DataAccessError
from app.schemas.cart import Cart, CartLine, CartStatus


@pytest.fixture
def cart_file(tmp_path):
    return tmp_path / "carts.json"


def test_missing_file_means_no_carts(cart_file):
    repo = CartRepository(cart_file)
    assert repo.list_all() == []
    assert repo.get_active_for_customer(4) is None


def test_add_assigns_ids_that_survive_reload(cart_file):
    repo = CartRepository(cart_file)
    first = repo.add(4)
    second = repo.add(5)
    assert (first.id, second.id) == (1, 2)
    reloaded = CartRepository(cart_file)
    assert reloaded.get_by_id(2).customer_id == 5
    assert reloaded.get_by_id(1).status == CartStatus.active


def test_save_round_trip(cart_file):
    repo = CartRepository(cart_file)
    cart = repo.add(4)
    cart.items.append(CartLine(menu_item_id=1, quantity=2))
    cart.restaurant_id = 1
    repo.save(cart)
    loaded = CartRepository(cart_file).get_by_id(cart.id)
    assert loaded.restaurant_id == 1
    assert loaded.items == [CartLine(menu_item_id=1, quantity=2)]


def test_ids_are_not_reused_after_checkout(cart_file):
    repo = CartRepository(cart_file)
    first = repo.add(4)
    repo.save(first.model_copy(update={"status": CartStatus.checked_out}))
    second = repo.add(4)
    assert second.id == first.id + 1


def test_active_lookup_ignores_checked_out_carts(cart_file):
    cart_file.write_text(json.dumps([
        {"id": 1, "customer_id": 4, "restaurant_id": 1, "status": "checked_out",
         "items": [{"menu_item_id": 1, "quantity": 1}]},
        {"id": 2, "customer_id": 4, "restaurant_id": None, "status": "active", "items": []},
    ]))
    assert CartRepository(cart_file).get_active_for_customer(4).id == 2


def test_only_one_active_cart_per_customer(cart_file):
    repo = CartRepository(cart_file)
    repo.add(4)
    with pytest.raises(DataAccessError):
        repo.add(4)


def test_get_unknown_and_save_unknown_raise(cart_file):
    repo = CartRepository(cart_file)
    with pytest.raises(CartNotFoundError):
        repo.get_by_id(9)
    with pytest.raises(CartNotFoundError):
        repo.save(Cart(id=9, customer_id=4))


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        json.dumps({"id": 1}),  # not a list
        json.dumps([{"id": 1, "customer_id": 4, "items": [{"menu_item_id": 1, "quantity": 0}]}]),
        json.dumps([{"id": 1, "customer_id": 4}, {"id": 1, "customer_id": 5}]),  # duplicate IDs
        json.dumps([{"id": 1, "customer_id": 4}, {"id": 2, "customer_id": 4}]),  # two active carts
    ],
)
def test_invalid_file_raises_data_access_error(cart_file, content):
    cart_file.write_text(content)
    with pytest.raises(DataAccessError):
        CartRepository(cart_file).list_all()


def test_committed_carts_file_is_valid():
    from app.core.config import PROJECT_ROOT

    CartRepository(PROJECT_ROOT / "data" / "carts.json").list_all()
