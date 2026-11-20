"""Customer page shows the selected restaurant's menu, loaded from the API (#68).

The page has no JavaScript test runner, so the script and page checks look at what is served,
and the API checks call the same endpoint the page uses with temporary data.
"""

import json

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_menu_repository
from app.main import app
from app.repositories.menu_repository import MenuRepository
from app.repositories.restaurant_repository import RestaurantRepository

page_client = TestClient(app)

RESTAURANTS = [
    {"id": 1, "name": "Test Pizza", "cuisine": "Italian"},
    {"id": 2, "name": "Empty Kitchen", "cuisine": "Greek"},
]
MENU_ITEMS = [
    {"id": 1, "restaurant_id": 1, "name": "Margherita", "description": "Tomato and basil",
     "price": 16.99, "is_available": True, "category": "Pizza", "image_url": ""},
    {"id": 2, "restaurant_id": 1, "name": "Tiramisu", "description": "",
     "price": 7.5, "is_available": False, "category": "Desserts", "image_url": ""},
]


@pytest.fixture
def api_client(tmp_path):
    restaurant_file = tmp_path / "restaurants.json"
    menu_file = tmp_path / "menus.json"
    restaurant_file.write_text(json.dumps(RESTAURANTS), encoding="utf-8")
    menu_file.write_text(json.dumps(MENU_ITEMS), encoding="utf-8")
    app.dependency_overrides[get_menu_repository] = lambda: MenuRepository(
        menu_file, RestaurantRepository(restaurant_file)
    )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_menu_repository, None)


def test_details_panel_has_a_menu_section():
    html = page_client.get("/").text
    assert 'id="menu-list"' in html
    assert 'id="menu-status"' in html


def test_api_script_loads_the_menu_by_restaurant_id():
    script = page_client.get("/static/api.js").text
    assert "getMenu(restaurantId)" in script
    assert "/restaurants/${restaurantId}/menu" in script


def test_page_script_shows_menu_fields_from_the_api():
    script = page_client.get("/static/app.js").text
    assert "API.getMenu(" in script
    for field in ("menuItem.name", "menuItem.price", "menuItem.description", "menuItem.is_available"):
        assert field in script, field


def test_page_script_has_empty_and_error_messages():
    script = page_client.get("/static/app.js").text
    assert "no menu items yet" in script
    assert "Could not load the menu" in script


def test_menu_is_not_hard_coded_in_the_page():
    html = page_client.get("/").text
    script = page_client.get("/static/app.js").text
    for name in ("Kung Pao Chicken", "Margherita", "Spring Rolls"):
        assert name not in html
        assert name not in script


def test_menu_endpoint_used_by_the_page_returns_fields_it_shows(api_client):
    response = api_client.get("/restaurants/1/menu")
    assert response.status_code == 200
    items = response.json()["items"]
    assert [i["name"] for i in items] == ["Margherita", "Tiramisu"]
    for item in items:
        assert {"name", "description", "price", "is_available"} <= item.keys()
    assert items[1]["is_available"] is False


def test_menu_endpoint_returns_empty_list_for_restaurant_without_items(api_client):
    # The page shows its "no menu items" message for this response.
    response = api_client.get("/restaurants/2/menu")
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_menu_endpoint_returns_404_with_message_for_unknown_restaurant(api_client):
    # The page shows this detail text instead of failing silently.
    response = api_client.get("/restaurants/99/menu")
    assert response.status_code == 404
    assert response.json()["detail"] == "Restaurant 99 not found"
