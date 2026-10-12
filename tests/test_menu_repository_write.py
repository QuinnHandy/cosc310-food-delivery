import json

import pytest
from pydantic import ValidationError

from app.repositories.menu_repository import MenuItemNotFoundError, MenuRepository
from app.repositories.restaurant_repository import (
    DataAccessError,
    RestaurantNotFoundError,
    RestaurantRepository,
)
from app.schemas.menu import MenuItemCreate, MenuItemUpdate

RESTAURANTS = [
    {"id": 1, "name": "Test Pizza", "cuisine": "Italian"},
    {"id": 2, "name": "Test Sushi", "cuisine": "Japanese"},
]


def entry(id, restaurant_id, **overrides):
    base = {"id": id, "restaurant_id": restaurant_id, "name": f"Item {id}",
            "description": "", "price": 9.99, "is_available": True,
            "category": "Mains", "image_url": ""}
    return {**base, **overrides}


def make_repo(tmp_path, items):
    restaurant_file = tmp_path / "restaurants.json"
    menu_file = tmp_path / "menus.json"
    restaurant_file.write_text(json.dumps(RESTAURANTS), encoding="utf-8")
    menu_file.write_text(json.dumps(items), encoding="utf-8")
    return MenuRepository(menu_file, RestaurantRepository(restaurant_file)), menu_file, restaurant_file


NEW_ITEM = MenuItemCreate(name="Garlic Knots", price=7.5, category="Starters")


# New item IDs are unique across the whole file, not just per restaurant.
def test_add_item_gets_next_global_id(tmp_path):
    repo, _, _ = make_repo(tmp_path, [entry(1, 1), entry(5, 2)])

    created = repo.add_item(1, NEW_ITEM)

    assert created.id == 6
    assert created.restaurant_id == 1
    assert [i.id for i in repo.get_menu(1).items] == [1, 6]
    assert [i.id for i in repo.get_menu(2).items] == [5]


# Data written survives a restart and the file still loads cleanly.
def test_added_item_loads_after_restart(tmp_path):
    repo, menu_file, restaurant_file = make_repo(tmp_path, [entry(1, 1)])
    repo.add_item(1, NEW_ITEM)

    restarted = MenuRepository(menu_file, RestaurantRepository(restaurant_file))

    assert [i.name for i in restarted.get_menu(1).items] == ["Item 1", "Garlic Knots"]
    assert list(tmp_path.glob("*.tmp")) == []


# Partial update changes only the fields sent; ID and restaurant stay the same.
def test_update_item_changes_only_sent_fields(tmp_path):
    repo, _, _ = make_repo(tmp_path, [entry(1, 1)])

    updated = repo.update_item(1, 1, MenuItemUpdate(price=8.25, is_available=False))

    assert (updated.id, updated.restaurant_id) == (1, 1)
    assert updated.price == 8.25
    assert updated.is_available is False
    assert updated.name == "Item 1"


# Failure case: adding to a restaurant that does not exist.
def test_add_item_unknown_restaurant_raises(tmp_path):
    repo, _, _ = make_repo(tmp_path, [])

    with pytest.raises(RestaurantNotFoundError):
        repo.add_item(99, NEW_ITEM)


# Failure case: item exists but belongs to a different restaurant.
def test_update_item_of_other_restaurant_raises(tmp_path):
    repo, _, _ = make_repo(tmp_path, [entry(1, 1)])

    with pytest.raises(MenuItemNotFoundError):
        repo.update_item(2, 1, MenuItemUpdate(price=5))


# Failure case: an invalid price is rejected by the update model, so the file is never touched.
def test_update_item_invalid_price_rejected(tmp_path):
    repo, menu_file, _ = make_repo(tmp_path, [entry(1, 1)])
    before = menu_file.read_text(encoding="utf-8")

    with pytest.raises(ValidationError):
        repo.update_item(1, 1, MenuItemUpdate(price=-5))
    assert menu_file.read_text(encoding="utf-8") == before