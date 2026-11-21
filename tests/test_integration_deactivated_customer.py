"""Integration test (#102): a deactivated customer is blocked across cart and checkout, through
the real HTTP API only (Customer, Auth, Cart, Checkout and Order subsystems together).

Everything runs on a temporary copy of data/ (the `app_data` fixture in
tests/app_data_helpers.py). The first test also checks the committed data files are
byte-for-byte unchanged afterwards.

Seed menu: restaurant 1 (Golden Dragon) has item 1 ($15.50) and item 2 ($7.00).
"""

import hashlib
import json
from pathlib import Path

import pytest

from app.core.config import PROJECT_ROOT
from app_data_helpers import app_data  # noqa: F401  (pytest fixture)

DANA = {"name": "Dana Park", "email": "dana@example.com", "password": "longenough",
        "delivery_address": "1 Lake Rd"}
ELI = {"name": "Eli Stone", "email": "eli@example.com", "password": "longenough",
       "delivery_address": "2 Hill St"}


def sign_up_and_sign_in(client, customer: dict) -> tuple[dict[str, str], int]:
    """Registers a brand-new customer and signs in. Returns the auth header and customer ID.

    New customers (not the seeded ones) so the test never depends on carts or orders that
    already exist in data/.
    """
    assert client.post("/customers", json=customer).status_code == 201
    login = client.post(
        "/auth/login", json={"email": customer["email"], "password": customer["password"]}
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['token']}"}
    return headers, client.get("/customers/me", headers=headers).json()["id"]


def add_to_cart(client, headers, item_id=1, quantity=2) -> None:
    response = client.post(
        "/cart/items", json={"menu_item_id": item_id, "quantity": quantity}, headers=headers
    )
    assert response.status_code == 200


def snapshot(path: Path) -> bytes | None:
    """The file's exact bytes, or None if it does not exist (orders.json starts out missing in some setups)."""
    return path.read_bytes() if path.exists() else None


def fingerprint(directory: Path) -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(directory.glob("*.json"))}


def stored_cart(app_data, customer_id: int) -> dict:
    carts = json.loads((app_data.data_dir / "carts.json").read_text())
    return next(cart for cart in carts if cart["customer_id"] == customer_id)


@pytest.mark.parametrize("deactivated_by", ["self", "admin"])
def test_deactivated_customer_is_blocked_across_cart_and_checkout(app_data, deactivated_by):
    committed_before = fingerprint(PROJECT_ROOT / "data")
    client, admin = app_data.client, app_data.headers["admin"]

    # 1. A customer signs up, signs in and adds an item to their cart.
    me, customer_id = sign_up_and_sign_in(client, DANA)
    add_to_cart(client, me, item_id=1, quantity=2)
    carts_file, orders_file = app_data.data_dir / "carts.json", app_data.data_dir / "orders.json"
    carts_before, orders_before = snapshot(carts_file), snapshot(orders_file)

    # ...then their account is deactivated (by themselves, or by an admin).
    if deactivated_by == "self":
        deactivate = client.post("/customers/me/deactivate", headers=me)
    else:
        deactivate = client.post(f"/customers/{customer_id}/deactivate", headers=admin)
    assert deactivate.status_code == 200
    assert deactivate.json()["is_active"] is False

    # 2. Sign-in is refused, and the old token gets 403 on the cart and on checkout.
    login = client.post("/auth/login", json={"email": DANA["email"], "password": DANA["password"]})
    assert login.status_code == 403
    assert "deactivated" in login.json()["detail"]

    blocked = [
        ("GET", "/cart", None),
        ("POST", "/cart/items", {"menu_item_id": 2}),
        ("POST", "/checkout", None),
        # Every other way in with the same token is closed too.
        ("DELETE", "/cart/items", None),
        ("PATCH", "/cart/items/1", {"quantity": 5}),
        ("GET", "/customers/me/orders", None),
    ]
    for method, path, body in blocked:
        response = client.request(method, path, json=body, headers=me)
        assert response.status_code == 403, f"{method} {path} returned {response.status_code}"
        assert "deactivated" in response.json()["detail"], f"{method} {path}"

    # 3. No order was written, and the cart is exactly as it was.
    assert snapshot(orders_file) == orders_before
    assert snapshot(carts_file) == carts_before
    assert stored_cart(app_data, customer_id)["items"] == [{"menu_item_id": 1, "quantity": 2}]
    their_orders = client.get(f"/customers/{customer_id}/orders", headers=admin)
    assert their_orders.status_code == 200 and their_orders.json() == []

    # 4. Only the temporary copy of data/ was used.
    assert fingerprint(PROJECT_ROOT / "data") == committed_before


def test_deactivating_one_customer_does_not_block_another(app_data):
    """The 403 is about the deactivated account, not a broken cart or checkout."""
    client, admin = app_data.client, app_data.headers["admin"]
    dana, dana_id = sign_up_and_sign_in(client, DANA)
    eli, eli_id = sign_up_and_sign_in(client, ELI)
    add_to_cart(client, dana)
    add_to_cart(client, eli, item_id=2, quantity=1)

    assert client.post(f"/customers/{dana_id}/deactivate", headers=admin).status_code == 200

    assert client.post("/checkout", headers=dana).status_code == 403
    placed = client.post("/checkout", headers=eli)
    assert placed.status_code == 201
    assert placed.json()["customer_id"] == eli_id

    assert client.get(f"/customers/{dana_id}/orders", headers=admin).json() == []
    assert [o["id"] for o in client.get(f"/customers/{eli_id}/orders", headers=admin).json()] == [1]
