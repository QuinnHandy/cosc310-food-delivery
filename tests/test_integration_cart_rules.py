"""Integration test (#104): the cart's rules hold across the Customer, Auth, Restaurant/Menu
and Cart subsystems, through the real HTTP API only.

Everything runs on a temporary copy of data/ (tests/app_data_helpers.py), and the last test
checks the committed data files are byte-for-byte unchanged.

Seed menu: restaurant 1 (Golden Dragon) has item 1 ($15.50), item 2 ($7.00) and item 3
(unavailable); restaurant 2 (Spice Garden) starts at item 4.
"""

import hashlib
import json

import pytest

from app.core.config import PROJECT_ROOT
from app_data_helpers import app_data  # noqa: F401  (pytest fixture)

NEW_CUSTOMER = {"name": "Dana Park", "email": "dana@example.com", "password": "longenough",
                "delivery_address": "1 Lake Rd"}


def sign_up_and_sign_in(client) -> dict[str, str]:
    """Customer subsystem → Auth subsystem: a brand-new customer gets a working token."""
    assert client.post("/customers", json=NEW_CUSTOMER).status_code == 201
    login = client.post("/auth/login", json={"email": NEW_CUSTOMER["email"], "password": NEW_CUSTOMER["password"]})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['token']}"}


def cart_item_ids(client, headers) -> list[int]:
    return [line["menu_item_id"] for line in client.get("/cart", headers=headers).json()["items"]]


def test_new_customer_cannot_mix_restaurants_in_one_cart(app_data):
    client = app_data.client
    me = sign_up_and_sign_in(client)

    # Restaurant/Menu subsystem: find one item from each of two restaurants through the API.
    item_a = client.get("/restaurants/1/menu").json()["items"][0]
    item_b = client.get("/restaurants/2/menu").json()["items"][0]
    assert item_a["restaurant_id"] != item_b["restaurant_id"]

    first = client.post("/cart/items", json={"menu_item_id": item_a["id"]}, headers=me)
    assert first.status_code == 200
    assert first.json()["restaurant_id"] == 1

    mixed = client.post("/cart/items", json={"menu_item_id": item_b["id"]}, headers=me)
    assert mixed.status_code == 409
    assert "one restaurant" in mixed.json()["detail"]
    assert cart_item_ids(client, me) == [item_a["id"]]  # still only A's item

    # After clearing, the other restaurant is allowed.
    client.delete("/cart/items", headers=me)
    assert client.post("/cart/items", json={"menu_item_id": item_b["id"]}, headers=me).status_code == 200
    assert cart_item_ids(client, me) == [item_b["id"]]


@pytest.mark.parametrize("quantity", [0, -1, 21, "two", "3", 1.5, None])
def test_invalid_quantities_are_refused_and_change_nothing(app_data, quantity):
    client, me = app_data.client, app_data.headers["customer"]
    client.post("/cart/items", json={"menu_item_id": 1, "quantity": 2}, headers=me)
    before = (app_data.data_dir / "carts.json").read_bytes()

    add = client.post("/cart/items", json={"menu_item_id": 2, "quantity": quantity}, headers=me)
    patch = client.patch("/cart/items/1", json={"quantity": quantity}, headers=me)
    assert add.status_code == 422
    assert patch.status_code == 422
    assert (app_data.data_dir / "carts.json").read_bytes() == before


def test_nonexistent_unavailable_and_deactivated_items(app_data):
    client, me = app_data.client, app_data.headers["customer"]
    assert client.post("/cart/items", json={"menu_item_id": 9999}, headers=me).status_code == 404

    unavailable = next(i for i in client.get("/restaurants/1/menu").json()["items"] if not i["is_available"])
    assert client.post("/cart/items", json={"menu_item_id": unavailable["id"]}, headers=me).status_code == 409

    # Deactivate item 2 in the stored menu (the endpoint for this is #87), then try to add it.
    menu_file = app_data.data_dir / "menus.json"
    items = json.loads(menu_file.read_text())
    next(i for i in items if i["id"] == 2)["is_active"] = False
    menu_file.write_text(json.dumps(items))
    refused = client.post("/cart/items", json={"menu_item_id": 2}, headers=me)
    assert refused.status_code == 409
    assert "not available" in refused.json()["detail"]
    assert cart_item_ids(client, me) == []


def test_requests_without_the_right_user_are_refused(app_data):
    client, h = app_data.client, app_data.headers
    assert client.get("/cart").status_code == 401
    assert client.post("/cart/items", json={"menu_item_id": 1}).status_code == 401
    assert client.get("/cart", headers={"Authorization": "Bearer not-a-real-token"}).status_code == 401
    assert client.get("/cart", headers=h["owner1"]).status_code == 403  # owners have no cart
    assert client.get("/cart", headers=h["admin"]).status_code == 403
    # Customers can't edit restaurants either (Restaurant subsystem's own guard).
    assert client.patch("/restaurants/1", json={"name": "Hacked"}, headers=h["customer"]).status_code == 403
    assert client.get("/restaurants/1").json()["name"] == "Golden Dragon"


def test_customer_deactivated_by_admin_is_locked_out_of_their_cart(app_data):
    client = app_data.client
    me = sign_up_and_sign_in(client)
    client.post("/cart/items", json={"menu_item_id": 1, "quantity": 2}, headers=me)
    customer_id = client.get("/customers/me", headers=me).json()["id"]

    # Customer subsystem (admin) → Auth → Cart: the same token stops working for the cart.
    assert client.post(f"/customers/{customer_id}/deactivate", headers=app_data.headers["admin"]).status_code == 200
    assert client.get("/cart", headers=me).status_code == 403
    assert client.post("/cart/items", json={"menu_item_id": 2}, headers=me).status_code == 403
    assert client.delete("/cart/items", headers=me).status_code == 403

    # The cart itself is kept, not deleted, with its items.
    carts = json.loads((app_data.data_dir / "carts.json").read_text())
    kept = next(c for c in carts if c["customer_id"] == customer_id)
    assert kept["items"] == [{"menu_item_id": 1, "quantity": 2}]


def _fingerprint(directory):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(directory.glob("*.json"))}


def test_running_the_whole_flow_leaves_committed_data_unchanged(app_data):
    before = _fingerprint(PROJECT_ROOT / "data")
    test_new_customer_cannot_mix_restaurants_in_one_cart(app_data)  # registers, signs in, uses the cart
    client, admin = app_data.client, app_data.headers["admin"]
    assert client.post("/customers/5/deactivate", headers=admin).status_code == 200
    assert _fingerprint(PROJECT_ROOT / "data") == before
    assert _fingerprint(app_data.data_dir) != _fingerprint(PROJECT_ROOT / "data")  # the copy did change
