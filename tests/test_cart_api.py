"""Cart endpoints (#89-#92) through HTTP, on a temporary copy of all data."""

import json

import pytest

from app.core.config import PROJECT_ROOT
from app_data_helpers import app_data  # noqa: F401  (pytest fixture)


@pytest.fixture
def api(app_data):
    return app_data.client, app_data.headers


def test_get_cart_needs_an_active_customer(api):
    client, h = api
    assert client.get("/cart").status_code == 401
    assert client.get("/cart", headers=h["owner1"]).status_code == 403
    assert client.get("/cart", headers=h["admin"]).status_code == 403
    assert client.get("/cart", headers=h["deactivated"]).status_code == 403


def test_get_cart_returns_same_empty_cart(api):
    client, h = api
    first = client.get("/cart", headers=h["customer"])
    assert first.status_code == 200
    body = first.json()
    assert body["items"] == [] and body["total"] == 0 and body["restaurant_id"] is None
    assert client.get("/cart", headers=h["customer"]).json()["id"] == body["id"]


def test_add_update_remove_clear_flow(api):
    client, h = api
    c = h["customer"]
    added = client.post("/cart/items", json={"menu_item_id": 1, "quantity": 2}, headers=c)
    assert added.status_code == 200
    assert added.json()["items"][0]["line_total"] == 31.0
    assert added.json()["total"] == 35.99

    client.post("/cart/items", json={"menu_item_id": 2}, headers=c)  # quantity defaults to 1
    changed = client.patch("/cart/items/2", json={"quantity": 3}, headers=c)
    assert changed.status_code == 200
    assert changed.json()["subtotal"] == 52.0  # 31 + 21

    removed = client.delete("/cart/items/1", headers=c)
    assert [l["menu_item_id"] for l in removed.json()["items"]] == [2]

    cleared = client.delete("/cart/items", headers=c)
    assert cleared.status_code == 200
    assert cleared.json()["items"] == [] and cleared.json()["id"] == added.json()["id"]


@pytest.mark.parametrize("quantity", [0, -1, 21, "2", 2.5, "abc", True])
def test_invalid_quantity_returns_422(api, quantity):
    client, h = api
    response = client.post("/cart/items", json={"menu_item_id": 1, "quantity": quantity}, headers=h["customer"])
    assert response.status_code == 422


def test_going_over_20_in_total_returns_422_with_message(api):
    client, h = api
    client.post("/cart/items", json={"menu_item_id": 1, "quantity": 18}, headers=h["customer"])
    response = client.post("/cart/items", json={"menu_item_id": 1, "quantity": 3}, headers=h["customer"])
    assert response.status_code == 422
    assert "at most 20" in response.json()["detail"]


def test_unknown_unavailable_and_other_restaurant_items(api):
    client, h = api
    c = h["customer"]
    assert client.post("/cart/items", json={"menu_item_id": 999}, headers=c).status_code == 404
    unavailable = client.post("/cart/items", json={"menu_item_id": 3}, headers=c)
    assert unavailable.status_code == 409 and "not available" in unavailable.json()["detail"]
    client.post("/cart/items", json={"menu_item_id": 1}, headers=c)
    mixed = client.post("/cart/items", json={"menu_item_id": 4}, headers=c)
    assert mixed.status_code == 409
    assert "one restaurant" in mixed.json()["detail"]


def test_patch_and_delete_of_item_not_in_cart_return_404(api):
    client, h = api
    assert client.patch("/cart/items/1", json={"quantity": 2}, headers=h["customer"]).status_code == 404
    assert client.delete("/cart/items/1", headers=h["customer"]).status_code == 404


def test_client_cannot_send_a_price(api):
    client, h = api
    response = client.post(
        "/cart/items", json={"menu_item_id": 1, "quantity": 1, "price": 0.01}, headers=h["customer"]
    )
    # The extra field is ignored; the price comes from the menu.
    assert response.json()["items"][0]["unit_price"] == 15.5


def test_cart_is_saved_to_the_temp_data_not_the_committed_file(app_data):
    real_file = PROJECT_ROOT / "data" / "carts.json"  # git-ignored, so it may not exist

    def snapshot():
        return real_file.read_text() if real_file.exists() else None

    before = snapshot()
    app_data.client.post("/cart/items", json={"menu_item_id": 1}, headers=app_data.headers["customer"])
    saved = json.loads((app_data.data_dir / "carts.json").read_text())
    assert saved[0]["items"] == [{"menu_item_id": 1, "quantity": 1}]
    assert "price" not in json.dumps(saved)  # prices are never stored in the cart
    assert snapshot() == before


def test_cart_endpoints_are_documented(app_data):
    paths = app_data.client.get("/openapi.json").json()["paths"]
    assert {"401", "403", "404", "409", "422"} <= paths["/cart/items"]["post"]["responses"].keys()
    assert "404" in paths["/cart/items/{menu_item_id}"]["patch"]["responses"]
