
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.routes.menus import get_menu_repository
from app.repositories.menu_repository import MenuRepository
from app.repositories.restaurant_repository import RestaurantRepository


@pytest.fixture
def client(tmp_path):
    restaurants_file = tmp_path / "restaurants.json"
    menus_file = tmp_path / "menus.json"

    restaurants_file.write_text(
        json.dumps([
            {"id": 1, "name": "Pizza Place", "cuisine": "Italian"}
        ]),
        encoding="utf-8",
    )
    menus_file.write_text("[]", encoding="utf-8")

    def test_repository():
        restaurant_repository = RestaurantRepository(restaurants_file)
        return MenuRepository(menus_file, restaurant_repository)

    app.dependency_overrides[get_menu_repository] = test_repository

    try:
        with TestClient(app) as test_client:
            yield test_client, menus_file, restaurants_file
    finally:
        app.dependency_overrides.pop(get_menu_repository, None)


def test_add_menu_item(client):
    test_client, menus_file, restaurants_file = client

    response = test_client.post(
        "/restaurants/1/menu",
        json={
            "name": "Margherita Pizza",
            "description": "Tomato, mozzarella, basil",
            "price": 14.50,
            "category": "Mains",
        },
    )

    assert response.status_code == 201

    item = response.json()
    assert item["id"] == 1
    assert item["restaurant_id"] == 1
    assert item["name"] == "Margherita Pizza"
    assert item["price"] == 14.50
    assert item["is_available"] is True

    saved_items = json.loads(menus_file.read_text(encoding="utf-8"))
    assert saved_items == [item]

    # Confirm persistence using a fresh repository instance.
    repository = MenuRepository(
        menus_file,
        RestaurantRepository(restaurants_file),
    )
    assert repository.get_menu(1).items[0].name == "Margherita Pizza"


def test_add_menu_item_unknown_restaurant(client):
    test_client, menus_file, _ = client

    response = test_client.post(
        "/restaurants/999/menu",
        json={
            "name": "Pizza",
            "price": 12.00,
            "category": "Mains",
        },
    )

    assert response.status_code == 404
    assert json.loads(menus_file.read_text(encoding="utf-8")) == []


@pytest.mark.parametrize(
    "invalid_item",
    [
        {"name": "", "price": 12.00, "category": "Mains"},
        {"name": "Pizza", "price": -5.00, "category": "Mains"},
        {"name": "Pizza", "price": 0, "category": "Mains"},
        {"name": "Pizza", "price": 12.00, "category": ""},
        {"name": "Pizza", "category": "Mains"},
    ],
)
def test_add_menu_item_invalid_input(client, invalid_item):
    test_client, menus_file, _ = client

    response = test_client.post(
        "/restaurants/1/menu",
        json=invalid_item,
    )

    assert response.status_code == 422
    assert json.loads(menus_file.read_text(encoding="utf-8")) == []


def test_add_menu_items_get_unique_ids(client):
    test_client, menus_file, _ = client

    for name in ["Pizza", "Pasta"]:
        response = test_client.post(
            "/restaurants/1/menu",
            json={
                "name": name,
                "price": 12.00,
                "category": "Mains",
            },
        )
        assert response.status_code == 201

    saved_items = json.loads(menus_file.read_text(encoding="utf-8"))
    assert [item["id"] for item in saved_items] == [1, 2]
    assert all(item["restaurant_id"] == 1 for item in saved_items)
