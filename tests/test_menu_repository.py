import json

import pytest

from app.repositories.menu_repository import MenuRepository, RestaurantNotFoundError
from app.repositories.restaurant_repository import DataAccessError, RestaurantRepository
from app.schemas.menu import MenuItem


def make_repo(tmp_path, restaurants, items):
    restaurant_file = tmp_path / "restaurants.json"
    menu_file = tmp_path / "menus.json"
    restaurant_file.write_text(json.dumps(restaurants), encoding="utf-8")
    menu_file.write_text(json.dumps(items), encoding="utf-8")
    return MenuRepository(menu_file, RestaurantRepository(restaurant_file))


RESTAURANTS = [
    {"id": 1, "name": "Test Pizza", "cuisine": "Italian"},
    {"id": 2, "name": "Test Sushi", "cuisine": "Japanese"},
]


def item(id, restaurant_id, **overrides):
    base = {"id": id, "restaurant_id": restaurant_id, "name": f"Item {id}",
            "description": "desc", "price": 9.99, "is_available": True,
            "category": "Mains", "image_url": ""}
    return {**base, **overrides}


# Tests that a restaurant's menu returns only its own items.
def test_get_menu_returns_items_for_restaurant(tmp_path):
    repo = make_repo(tmp_path, RESTAURANTS, [item(2, 1), item(1, 1), item(3, 2)])

    menu = repo.get_menu(1)

    assert menu.restaurant_id == 1
    assert [i.id for i in menu.items] == [1, 2]


# Tests that an existing restaurant with no items gets an empty menu.
def test_get_menu_empty_for_restaurant_without_items(tmp_path):
    repo = make_repo(tmp_path, RESTAURANTS, [item(1, 1)])

    assert repo.get_menu(2).items == []


# Failure case: unknown restaurant ID.
def test_get_menu_unknown_restaurant_raises(tmp_path):
    repo = make_repo(tmp_path, RESTAURANTS, [item(1, 1)])

    with pytest.raises(RestaurantNotFoundError):
        repo.get_menu(99)


# Failure case: menu item pointing at a restaurant that does not exist (orphan).
def test_orphan_menu_item_rejected(tmp_path):
    repo = make_repo(tmp_path, RESTAURANTS, [item(1, 1), item(2, 42)])

    with pytest.raises(DataAccessError):
        repo.get_menu(1)


# Failure case: invalid JSON in the menu file.
def test_invalid_menu_json_rejected(tmp_path):
    repo = make_repo(tmp_path, RESTAURANTS, [])
    (tmp_path / "menus.json").write_text("not valid json", encoding="utf-8")

    with pytest.raises(DataAccessError):
        repo.get_menu(1)


# Failure case: negative price fails model validation.
def test_negative_price_rejected(tmp_path):
    repo = make_repo(tmp_path, RESTAURANTS, [item(1, 1, price=-1)])

    with pytest.raises(DataAccessError):
        repo.get_menu(1)


# Tests the real data files are consistent (no orphans) and the model fields.
def test_real_menu_data_has_no_orphans():
    from app.core.config import settings

    repo = MenuRepository(
        settings.data_dir / "menus.json",
        RestaurantRepository(settings.data_dir / "restaurants.json"),
    )
    for restaurant_id in range(1, 6):
        assert repo.get_menu(restaurant_id).items
    assert MenuItem.model_fields.keys() >= {
        "id", "restaurant_id", "name", "description", "price", "is_available", "category", "image_url",
    }