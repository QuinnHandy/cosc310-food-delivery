"""POST /checkout (#94) through HTTP, on a temporary copy of all data."""

import json

import pytest

from app.core.config import PROJECT_ROOT
from app.repositories.menu_repository import MenuRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.repositories.user_repository import UserRepository
from app.schemas.menu import MenuItemUpdate
from app.schemas.user import UserUpdate
from app_data_helpers import app_data  # noqa: F401  (pytest fixture)


@pytest.fixture
def api(app_data):
    return app_data.client, app_data.headers


def change_menu_item(app_data, restaurant_id, item_id, **changes):
    """Edits a menu item in the temp data, as an owner would (the owner endpoint for this is #87)."""
    restaurants = RestaurantRepository(app_data.data_dir / "restaurants.json")
    menus = MenuRepository(app_data.data_dir / "menus.json", restaurants)
    menus.update_item(restaurant_id, item_id, MenuItemUpdate(**changes))


def add_to_cart(client, headers, item_id=1, quantity=2):
    response = client.post(
        "/cart/items", json={"menu_item_id": item_id, "quantity": quantity}, headers=headers
    )
    assert response.status_code == 200
    return response.json()


def test_checkout_returns_201_and_the_created_order(api):
    client, h = api
    add_to_cart(client, h["customer"], 1, 2)
    response = client.post("/checkout", headers=h["customer"])
    assert response.status_code == 201
    order = response.json()
    assert order["id"] == 1 and order["customer_id"] == 4 and order["status"] == "placed"
    assert order["restaurant_name"] == "Golden Dragon"
    assert order["items"][0]["name"] == "Kung Pao Chicken"
    assert (order["subtotal"], order["delivery_fee"], order["total"]) == (31.0, 4.99, 35.99)
    assert order["delivery_address"] == "123 Main St, Kelowna, BC"
    assert "created_at" in order


def test_after_checkout_the_next_cart_is_new_and_empty(api):
    client, h = api
    first_cart = add_to_cart(client, h["customer"])
    client.post("/checkout", headers=h["customer"])
    new_cart = client.get("/cart", headers=h["customer"]).json()
    assert new_cart["id"] != first_cart["id"]
    assert new_cart["items"] == [] and new_cart["status"] == "active"


def test_checkout_needs_an_active_customer(api):
    client, h = api
    assert client.post("/checkout").status_code == 401
    assert client.post("/checkout", headers=h["owner1"]).status_code == 403
    assert client.post("/checkout", headers=h["admin"]).status_code == 403
    assert client.post("/checkout", headers=h["deactivated"]).status_code == 403


def test_empty_cart_returns_409_and_saves_no_order(api):
    client, h = api
    response = client.post("/checkout", headers=h["customer"])
    assert response.status_code == 409
    assert response.json()["detail"] == "Your cart is empty"


def test_checkout_without_a_cart_returns_409_and_writes_no_files(app_data):
    client, h = app_data.client, app_data.headers
    assert client.post("/checkout", headers=h["customer"]).status_code == 409
    assert not (app_data.data_dir / "carts.json").exists()
    assert json.loads((app_data.data_dir / "orders.json").read_text()) == []


def test_price_changed_before_checkout_uses_the_new_price(app_data):
    client, h = app_data.client, app_data.headers
    add_to_cart(client, h["customer"], 1, 1)
    change_menu_item(app_data, 1, 1, price=20.0)
    order = client.post("/checkout", headers=h["customer"]).json()
    assert order["items"][0]["unit_price"] == 20.0
    assert order["total"] == 24.99


def test_item_made_unavailable_before_checkout_returns_409_and_writes_nothing(app_data):
    client, h = app_data.client, app_data.headers
    add_to_cart(client, h["customer"], 2, 1)
    change_menu_item(app_data, 1, 2, is_available=False)

    response = client.post("/checkout", headers=h["customer"])
    assert response.status_code == 409
    assert "Vegetable Spring Rolls" in response.json()["detail"]
    assert json.loads((app_data.data_dir / "orders.json").read_text()) == []
    assert client.get("/cart", headers=h["customer"]).json()["items"][0]["menu_item_id"] == 2


def test_customer_without_delivery_address_returns_422(app_data):
    client, h = app_data.client, app_data.headers
    add_to_cart(client, h["customer"])
    restaurants = RestaurantRepository(app_data.data_dir / "restaurants.json")
    UserRepository(app_data.data_dir / "users.json", restaurants).update(
        4, UserUpdate(delivery_address="")
    )
    response = client.post("/checkout", headers=h["customer"])
    assert response.status_code == 422
    assert "delivery address" in response.json()["detail"]


def test_checkout_saves_to_the_temp_data_not_the_committed_file(app_data):
    committed = (PROJECT_ROOT / "data" / "orders.json").read_text()
    add_to_cart(app_data.client, app_data.headers["customer"])
    app_data.client.post("/checkout", headers=app_data.headers["customer"])
    saved = json.loads((app_data.data_dir / "orders.json").read_text())
    assert len(saved) == 1 and saved[0]["customer_id"] == 4
    assert (PROJECT_ROOT / "data" / "orders.json").read_text() == committed


def test_customers_cannot_send_prices_or_a_body(api):
    client, h = api
    add_to_cart(client, h["customer"], 1, 1)
    response = client.post("/checkout", json={"total": 0.01}, headers=h["customer"])
    assert response.status_code == 201
    assert response.json()["total"] == 20.49  # 15.50 + 4.99, from the menu


def test_checkout_is_documented(app_data):
    spec = app_data.client.get("/openapi.json").json()["paths"]["/checkout"]["post"]
    assert spec["summary"] == "Check out my cart"
    assert {"201", "401", "403", "409", "422", "500"} <= spec["responses"].keys()
