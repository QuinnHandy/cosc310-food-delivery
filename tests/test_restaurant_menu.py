import json
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.api.routes.restaurants import get_menu_repository
from app.main import app
from app.repositories.menu_repository import MenuRepository
from app.repositories.restaurant_repository import (
    RestaurantNotFoundError,
    RestaurantRepository,
)
from app.schemas.menu import Menu, MenuItem
from app.services.menu_service import MenuService

RESTAURANTS = [
    {"id": 1, "name": "Test Pizza", "cuisine": "Italian"},
    {"id": 2, "name": "Test Sushi", "cuisine": "Japanese"},
    {"id": 3, "name": "Empty Kitchen", "cuisine": "Greek"},
]


def item(id, restaurant_id, **overrides):
    base = {"id": id, "restaurant_id": restaurant_id, "name": f"Item {id}",
            "description": "desc", "price": 9.99, "is_available": True,
            "category": "Mains", "image_url": ""}
    return {**base, **overrides}


# Stored out of order, with items for other restaurants mixed in.
MENU_ITEMS = [
    item(3, 1, name="Garlic Knots", category="Starters", price=7.5),
    item(2, 2, name="Salmon Roll"),
    item(1, 1, name="Margherita", category="Pizza", price=16.99),
    item(4, 1, name="Tiramisu", category="Desserts", is_available=False),
]


# Points the app at temporary data files so tests never touch the real data directory.
@pytest.fixture
def client(tmp_path):
    restaurant_file = tmp_path / "restaurants.json"
    menu_file = tmp_path / "menus.json"
    restaurant_file.write_text(json.dumps(RESTAURANTS), encoding="utf-8")
    menu_file.write_text(json.dumps(MENU_ITEMS), encoding="utf-8")
    app.dependency_overrides[get_menu_repository] = lambda: MenuRepository(
        menu_file, RestaurantRepository(restaurant_file)
    )
    yield TestClient(app)
    app.dependency_overrides.clear()


# --- Route tests ---

def test_get_menu_returns_all_items_for_restaurant(client):
    response = client.get("/restaurants/1/menu")

    assert response.status_code == 200
    body = response.json()
    assert body["restaurant_id"] == 1
    assert [i["id"] for i in body["items"]] == [1, 3, 4]
    assert body["items"][0] == item(1, 1, name="Margherita", category="Pizza", price=16.99)


def test_get_menu_includes_unavailable_items(client):
    items = client.get("/restaurants/1/menu").json()["items"]

    assert {i["name"]: i["is_available"] for i in items}["Tiramisu"] is False


def test_get_menu_restaurant_without_items_returns_empty_list(client):
    response = client.get("/restaurants/3/menu")

    assert response.status_code == 200
    assert response.json() == {"restaurant_id": 3, "items": []}


# Failure case: unknown restaurant ID.
def test_get_menu_unknown_restaurant_returns_404(client):
    response = client.get("/restaurants/99/menu")

    assert response.status_code == 404
    assert response.json() == {"detail": "Restaurant 99 not found"}


# Failure case: non-integer restaurant ID.
def test_get_menu_non_integer_id_returns_422(client):
    response = client.get("/restaurants/abc/menu")

    assert response.status_code == 422


def test_menu_endpoint_documented_in_openapi(client):
    operation = client.get("/openapi.json").json()["paths"]["/restaurants/{restaurant_id}/menu"]["get"]

    assert operation["summary"] == "View a restaurant's menu"
    schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert schema == {"$ref": "#/components/schemas/MenuResponse"}
    assert "404" in operation["responses"]


# --- Service unit tests (repository mocked, no route or file involved) ---

def test_service_get_menu_returns_repository_result():
    repository = Mock(spec=MenuRepository)
    repository.get_menu.return_value = Menu(
        restaurant_id=1, items=[MenuItem(**item(1, 1, name="Margherita"))]
    )

    menu = MenuService(repository).get_menu(1)

    repository.get_menu.assert_called_once_with(1)
    assert [i.name for i in menu.items] == ["Margherita"]


def test_service_get_menu_unknown_restaurant_raises():
    repository = Mock(spec=MenuRepository)
    repository.get_menu.side_effect = RestaurantNotFoundError("Restaurant 99 not found")

    with pytest.raises(RestaurantNotFoundError):
        MenuService(repository).get_menu(99)
