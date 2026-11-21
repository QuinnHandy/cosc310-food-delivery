"""Integration test (#103): checkout revalidates price and availability that the restaurant owner
changed after the customer filled their cart.

Crosses the Auth, Restaurant/Menu (owner changes), Cart, Checkout and Order subsystems, through the
real HTTP API only. Everything runs on a temporary copy of data/ (tests/app_data_helpers.py), and
the last test checks the committed data files are byte-for-byte unchanged.

Seed data: Alice ("customer", user 4) is an active customer with a delivery address. Restaurant 1
(Golden Dragon) is owned by "owner1" and has item 1 Kung Pao Chicken ($15.50) and item 2
Vegetable Spring Rolls ($7.00). "owner2" owns restaurant 2.
"""

import hashlib
import json
from decimal import Decimal

from app.core.config import PROJECT_ROOT, settings
from app_data_helpers import app_data  # noqa: F401  (pytest fixture)

FEE = float(Decimal(settings.delivery_fee))


def fill_cart(client, customer):
    """Customer puts 2 x Kung Pao Chicken and 1 x Spring Rolls in their cart."""
    assert client.post("/cart/items", json={"menu_item_id": 1, "quantity": 2}, headers=customer).status_code == 200
    assert client.post("/cart/items", json={"menu_item_id": 2, "quantity": 1}, headers=customer).status_code == 200
    cart = client.get("/cart", headers=customer).json()
    assert cart["subtotal"] == 2 * 15.50 + 7.00
    return cart


def stored_orders(app_data):
    path = app_data.data_dir / "orders.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def test_price_raised_by_owner_before_checkout_is_charged_at_the_new_price(app_data):
    client, h = app_data.client, app_data.headers
    fill_cart(client, h["customer"])

    # Owner raises the price after the customer added the item.
    changed = client.patch("/restaurants/1/menu/items/1", json={"price": 18.00}, headers=h["owner1"])
    assert changed.status_code == 200

    # The cart already shows the new price, because it never stores prices.
    assert client.get("/cart", headers=h["customer"]).json()["subtotal"] == 2 * 18.00 + 7.00

    response = client.post("/checkout", headers=h["customer"])
    assert response.status_code == 201
    order = response.json()
    kung_pao = next(line for line in order["items"] if line["menu_item_id"] == 1)
    assert kung_pao["unit_price"] == 18.00
    assert kung_pao["line_total"] == 36.00
    assert order["subtotal"] == 43.00
    assert order["total"] == round(43.00 + FEE, 2)


def test_item_made_unavailable_before_checkout_is_refused_and_nothing_is_written(app_data):
    client, h = app_data.client, app_data.headers
    cart_before = fill_cart(client, h["customer"])

    off = client.patch("/restaurants/1/menu/items/2", json={"is_available": False}, headers=h["owner1"])
    assert off.status_code == 200

    response = client.post("/checkout", headers=h["customer"])
    assert response.status_code == 409
    assert "Vegetable Spring Rolls" in response.json()["detail"]
    assert stored_orders(app_data) == []

    # The cart is untouched, so the customer can fix it and try again.
    cart_after = client.get("/cart", headers=h["customer"]).json()
    assert cart_after["id"] == cart_before["id"]
    assert [(l["menu_item_id"], l["quantity"]) for l in cart_after["items"]] == [(1, 2), (2, 1)]
    assert client.get("/customers/me/orders", headers=h["customer"]).json() == []

    # Once the owner makes it available again, the same cart checks out.
    client.patch("/restaurants/1/menu/items/2", json={"is_available": True}, headers=h["owner1"])
    assert client.post("/checkout", headers=h["customer"]).status_code == 201
    assert len(stored_orders(app_data)) == 1


def test_item_deactivated_before_checkout_is_refused_and_nothing_is_written(app_data):
    client, h = app_data.client, app_data.headers
    fill_cart(client, h["customer"])

    assert client.delete("/restaurants/1/menu/items/1", headers=h["owner1"]).status_code == 204

    response = client.post("/checkout", headers=h["customer"])
    assert response.status_code == 409
    assert "Kung Pao Chicken" in response.json()["detail"]
    assert stored_orders(app_data) == []
    assert len(client.get("/cart", headers=h["customer"]).json()["items"]) == 2


def test_another_restaurants_owner_cannot_change_the_price(app_data):
    client, h = app_data.client, app_data.headers
    fill_cart(client, h["customer"])

    refused = client.patch("/restaurants/1/menu/items/1", json={"price": 1.00}, headers=h["owner2"])
    assert refused.status_code == 403

    order = client.post("/checkout", headers=h["customer"]).json()
    assert order["subtotal"] == 2 * 15.50 + 7.00  # original price, the change never happened


def test_order_keeps_its_snapshot_when_the_owner_changes_the_menu_afterwards(app_data):
    client, h = app_data.client, app_data.headers
    fill_cart(client, h["customer"])
    placed = client.post("/checkout", headers=h["customer"]).json()

    client.patch(
        "/restaurants/1/menu/items/1",
        json={"price": 25.00, "name": "Kung Pao Chicken (large)"},
        headers=h["owner1"],
    )
    client.patch("/restaurants/1/menu/items/2", json={"is_available": False}, headers=h["owner1"])

    fetched = client.get(f"/orders/{placed['id']}", headers=h["customer"]).json()
    assert fetched == placed
    kung_pao = next(line for line in fetched["items"] if line["menu_item_id"] == 1)
    assert (kung_pao["name"], kung_pao["unit_price"]) == ("Kung Pao Chicken", 15.50)

    listed = client.get("/customers/me/orders", headers=h["customer"]).json()
    assert [o["id"] for o in listed] == [placed["id"]]
    assert listed[0]["total"] == placed["total"]


def test_committed_data_is_unchanged(app_data):
    def digest():
        return {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((PROJECT_ROOT / "data").glob("*.json"))
        }

    before = digest()
    client, h = app_data.client, app_data.headers
    fill_cart(client, h["customer"])
    client.patch("/restaurants/1/menu/items/1", json={"price": 18.00}, headers=h["owner1"])
    client.post("/checkout", headers=h["customer"])
    assert digest() == before
