"""Issue #101: end-to-end customer checkout and restart persistence test."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import auth, cart, checkout, customers, menus, orders, restaurants
from app.core.config import PROJECT_ROOT, settings


def ok(response, status=200):
    """Require the expected HTTP response and return its JSON body."""
    assert response.status_code == status, response.text
    return response.json()


def fresh_api_app():
    """Build a new app using the same real API routers as app.main."""
    new_app = FastAPI()
    for module in (restaurants, menus, auth, customers, cart, checkout, orders):
        new_app.include_router(module.router)
    return new_app


def committed_json_snapshot():
    """Capture filenames and exact bytes to detect accidental writes to data/."""
    return {
        path.name: path.read_bytes()
        for path in (PROJECT_ROOT / "data").glob("*.json")
    }


def test_customer_to_order_workflow_survives_restart(client, temp_data_dir):
    before = committed_json_snapshot()
    assert temp_data_dir != PROJECT_ROOT / "data"

    # 1. Register a new customer using the public API.
    email = "m2-workflow-101@example.test"
    password = "Password123!"
    customer = ok(
        client.post(
            "/customers",
            json={
                "name": "Workflow Test Customer",
                "email": email,
                "password": password,
                "delivery_address": "101 Integration Lane, Kelowna, BC",
            },
        ),
        201,
    )
    customer_id = customer["id"]

    # 2. Sign in normally, not with a pre-seeded test token.
    login = ok(client.post("/auth/login", json={"email": email, "password": password}))
    assert login["user_id"] == customer_id
    assert login["role"] == "customer"
    headers = {"Authorization": f"Bearer {login['token']}"}

    # 3. Browse restaurants and fetch a menu through HTTP.
    restaurant_list = ok(client.get("/restaurants"))
    assert restaurant_list
    choice = None
    for restaurant in restaurant_list:
        menu = ok(client.get(f"/restaurants/{restaurant['id']}/menu"))
        available = [
            item for item in menu["items"]
            if item["is_available"] and item.get("is_active", True)
        ]
        if len(available) >= 2:
            choice = (restaurant, available[:2])
            break
    assert choice is not None, "Seed data needs a restaurant with two available items"
    restaurant, (first, second) = choice

    # 4. Add two distinct items; change the first item's quantity.
    ok(client.post("/cart/items", json={"menu_item_id": first["id"], "quantity": 1}, headers=headers))
    ok(client.post("/cart/items", json={"menu_item_id": second["id"], "quantity": 1}, headers=headers))
    ok(client.patch(f"/cart/items/{first['id']}", json={"quantity": 3}, headers=headers))

    # 5. Verify backend-calculated cart totals before placing the order.
    cart_before = ok(client.get("/cart", headers=headers))
    assert cart_before["restaurant_id"] == restaurant["id"]
    assert {line["menu_item_id"]: line["quantity"] for line in cart_before["items"]} == {
        first["id"]: 3, second["id"]: 1
    }
    expected_subtotal = round(first["price"] * 3 + second["price"], 2)
    assert cart_before["subtotal"] == pytest.approx(expected_subtotal)
    assert cart_before["delivery_fee"] > 0
    assert cart_before["total"] == pytest.approx(expected_subtotal + cart_before["delivery_fee"])

    # 6. Checkout; amounts and item snapshots must match the cart.
    order = ok(client.post("/checkout", headers=headers), 201)
    order_id = order["id"]
    assert order["status"] == "placed"
    assert order["delivery_address"] == customer["delivery_address"]
    assert len(order["items"]) == len(cart_before["items"])
    assert order["customer_id"] == customer_id
    assert order["restaurant_id"] == restaurant["id"]
    for amount in ("subtotal", "delivery_fee", "total"):
        assert order[amount] == pytest.approx(cart_before[amount])
    for cart_line, order_line in zip(cart_before["items"], order["items"]):
        for field in ("menu_item_id", "name", "quantity"):
            assert order_line[field] == cart_line[field]
        for field in ("unit_price", "line_total"):
            assert order_line[field] == pytest.approx(cart_line[field])

    # 7. Fetch the saved order and history through HTTP.
    assert ok(client.get(f"/orders/{order_id}", headers=headers)) == order
    history = ok(client.get("/customers/me/orders", headers=headers))
    assert [saved["id"] for saved in history] == [order_id]

    # 8. Checked-out cart is replaced by a new, empty active cart.
    empty_cart = ok(client.get("/cart", headers=headers))
    assert empty_cart["id"] != cart_before["id"]
    assert empty_cart["status"] == "active"
    assert empty_cart["items"] == []
    assert empty_cart["restaurant_id"] is None
    assert empty_cart["total"] == 0

    # 9. Simulate restart with a different FastAPI instance/client,
    # but keep the same temp JSON files and the original login token.
    assert settings.data_dir == temp_data_dir
    with TestClient(fresh_api_app()) as restarted_client:
        profile = ok(restarted_client.get("/customers/me", headers=headers))
        assert profile["id"] == customer_id
        assert profile["email"] == email
        assert ok(restarted_client.get(f"/orders/{order_id}", headers=headers)) == order

