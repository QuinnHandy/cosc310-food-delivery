"""GET /orders/{order_id} (#95) through HTTP, on a temporary copy of all data."""

import pytest

from app.repositories.menu_repository import MenuRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.schemas.menu import MenuItemUpdate
from app_data_helpers import app_data  # noqa: F401  (pytest fixture)


@pytest.fixture
def placed(app_data):
    """Alice has checked out 2 x Kung Pao Chicken; returns (app_data, order)."""
    client, h = app_data.client, app_data.headers
    client.post("/cart/items", json={"menu_item_id": 1, "quantity": 2}, headers=h["customer"])
    response = client.post("/checkout", headers=h["customer"])
    assert response.status_code == 201
    return app_data, response.json()


def test_owner_of_the_order_gets_200_with_snapshot_and_totals(placed):
    app_data, order = placed
    response = app_data.client.get(f"/orders/{order['id']}", headers=app_data.headers["customer"])
    assert response.status_code == 200
    assert response.json() == order
    body = response.json()
    assert body["items"] == [
        {"menu_item_id": 1, "name": "Kung Pao Chicken", "unit_price": 15.5, "quantity": 2, "line_total": 31.0}
    ]
    assert (body["subtotal"], body["delivery_fee"], body["total"]) == (31.0, 4.99, 35.99)


def test_another_customers_order_returns_403(placed):
    app_data, order = placed
    response = app_data.client.get(f"/orders/{order['id']}", headers=app_data.headers["customer2"])
    assert response.status_code == 403


def test_admin_can_see_any_order(placed):
    app_data, order = placed
    response = app_data.client.get(f"/orders/{order['id']}", headers=app_data.headers["admin"])
    assert response.status_code == 200 and response.json()["customer_id"] == 4


def test_restaurant_owner_and_deactivated_customer_return_403(placed):
    app_data, order = placed
    for who in ("owner1", "deactivated"):
        response = app_data.client.get(f"/orders/{order['id']}", headers=app_data.headers[who])
        assert response.status_code == 403, who


def test_unknown_order_returns_404(app_data):
    response = app_data.client.get("/orders/99", headers=app_data.headers["customer"])
    assert response.status_code == 404
    assert response.json()["detail"] == "Order 99 not found"
    assert app_data.client.get("/orders/99", headers=app_data.headers["admin"]).status_code == 404


def test_no_token_returns_401(placed):
    app_data, order = placed
    assert app_data.client.get(f"/orders/{order['id']}").status_code == 401


def test_non_integer_order_id_returns_422(app_data):
    assert app_data.client.get("/orders/abc", headers=app_data.headers["customer"]).status_code == 422


def test_changing_a_menu_items_price_or_name_does_not_change_the_stored_order(placed):
    app_data, order = placed
    restaurants = RestaurantRepository(app_data.data_dir / "restaurants.json")
    menus = MenuRepository(app_data.data_dir / "menus.json", restaurants)
    menus.update_item(1, 1, MenuItemUpdate(price=99.0, name="Renamed Dish"))

    response = app_data.client.get(f"/orders/{order['id']}", headers=app_data.headers["customer"])
    assert response.status_code == 200
    assert response.json() == order  # name, unit price and totals are exactly as at checkout
    assert response.json()["items"][0]["name"] == "Kung Pao Chicken"


def test_get_order_is_documented(app_data):
    spec = app_data.client.get("/openapi.json").json()["paths"]["/orders/{order_id}"]["get"]
    assert spec["summary"] == "Get one order"
    assert {"200", "401", "403", "404", "422", "500"} <= spec["responses"].keys()
    assert spec["parameters"][0]["description"]


# ---- listing orders (#96) ----

def checkout_as(app_data, who, item_id, quantity=1):
    client, h = app_data.client, app_data.headers
    client.post("/cart/items", json={"menu_item_id": item_id, "quantity": quantity}, headers=h[who])
    response = client.post("/checkout", headers=h[who])
    assert response.status_code == 201
    return response.json()


def test_my_orders_returns_only_my_orders_newest_first(app_data):
    first = checkout_as(app_data, "customer", 1)
    bobs = checkout_as(app_data, "customer2", 2)
    second = checkout_as(app_data, "customer", 2)

    response = app_data.client.get("/customers/me/orders", headers=app_data.headers["customer"])
    assert response.status_code == 200
    body = response.json()
    assert [o["id"] for o in body] == [second["id"], first["id"]]
    assert bobs["id"] not in [o["id"] for o in body]
    assert body[0] == second  # full order, with its item snapshot and totals


def test_my_orders_is_an_empty_list_not_404_when_there_are_none(app_data):
    response = app_data.client.get("/customers/me/orders", headers=app_data.headers["customer"])
    assert response.status_code == 200 and response.json() == []


def test_my_orders_needs_a_signed_in_active_customer(app_data):
    client, h = app_data.client, app_data.headers
    assert client.get("/customers/me/orders").status_code == 401
    for who in ("owner1", "admin", "deactivated"):
        assert client.get("/customers/me/orders", headers=h[who]).status_code == 403, who


def test_admin_can_list_a_customers_orders(app_data):
    order = checkout_as(app_data, "customer", 1)
    client, h = app_data.client, app_data.headers
    response = client.get("/customers/4/orders", headers=h["admin"])
    assert response.status_code == 200 and response.json() == [order]
    assert client.get("/customers/5/orders", headers=h["admin"]).json() == []


def test_admin_orders_for_unknown_customer_returns_404(app_data):
    client, h = app_data.client, app_data.headers
    response = client.get("/customers/99/orders", headers=h["admin"])
    assert response.status_code == 404
    assert response.json()["detail"] == "Customer 99 not found"
    assert client.get("/customers/2/orders", headers=h["admin"]).status_code == 404  # an owner, not a customer


def test_customer_orders_by_id_is_admin_only_and_needs_a_token(app_data):
    client, h = app_data.client, app_data.headers
    assert client.get("/customers/4/orders").status_code == 401
    for who in ("customer", "customer2", "owner1"):
        assert client.get("/customers/4/orders", headers=h[who]).status_code == 403, who


def test_non_integer_customer_id_returns_422(app_data):
    response = app_data.client.get("/customers/abc/orders", headers=app_data.headers["admin"])
    assert response.status_code == 422


def test_me_is_not_mistaken_for_a_customer_id(app_data):
    # /customers/me/orders must be the customer's own list, never the admin-by-ID route.
    response = app_data.client.get("/customers/me/orders", headers=app_data.headers["customer"])
    assert response.status_code == 200


def test_order_lists_are_documented(app_data):
    paths = app_data.client.get("/openapi.json").json()["paths"]
    mine = paths["/customers/me/orders"]["get"]
    assert mine["summary"] == "List my orders" and {"200", "401", "403", "500"} <= mine["responses"].keys()
    by_id = paths["/customers/{customer_id}/orders"]["get"]
    assert {"200", "401", "403", "404", "422", "500"} <= by_id["responses"].keys()
    assert by_id["parameters"][0]["description"]
