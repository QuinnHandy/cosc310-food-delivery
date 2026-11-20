"""Updating and deactivating menu items (#38, #87) through HTTP, on a temporary copy of all data.

Seed data: restaurant 1 (owner1) has items 1-3 (item 3 is unavailable); restaurant 2 (owner2)
has items 4-6. Alice (customer) is user 4.
"""

import json

import pytest

from app_data_helpers import app_data  # noqa: F401  (pytest fixture)


@pytest.fixture
def api(app_data):
    return app_data.client, app_data.headers


def stored_items(app_data):
    return json.loads((app_data.data_dir / "menus.json").read_text(encoding="utf-8"))


def menu_ids(client, restaurant_id=1):
    return [i["id"] for i in client.get(f"/restaurants/{restaurant_id}/menu").json()["items"]]


def add_to_cart(client, headers, item_id):
    return client.post("/cart/items", json={"menu_item_id": item_id}, headers=headers)


# ---- PATCH: availability (#87) and updates (#38) ----

def test_owner_can_make_an_item_unavailable_and_available_again(api):
    client, h = api
    off = client.patch("/restaurants/1/menu/items/1", json={"is_available": False}, headers=h["owner1"])
    assert off.status_code == 200 and off.json()["is_available"] is False
    blocked = add_to_cart(client, h["customer"], 1)
    assert blocked.status_code == 409 and "not available" in blocked.json()["detail"]

    on = client.patch("/restaurants/1/menu/items/1", json={"is_available": True}, headers=h["owner1"])
    assert on.status_code == 200 and on.json()["is_available"] is True
    assert add_to_cart(client, h["customer"], 1).status_code == 200


def test_unavailable_items_are_still_shown_but_marked_unavailable(api):
    client, h = api
    client.patch("/restaurants/1/menu/items/2", json={"is_available": False}, headers=h["owner1"])
    items = {i["id"]: i for i in client.get("/restaurants/1/menu").json()["items"]}
    assert items[2]["is_available"] is False
    assert items[3]["is_available"] is False  # seeded as unavailable, still listed
    assert items[1]["is_available"] is True


def test_patch_changes_only_the_fields_sent(api):
    client, h = api
    response = client.patch(
        "/restaurants/1/menu/items/1", json={"price": 16.25, "category": "Specials"}, headers=h["owner1"]
    )
    assert response.status_code == 200
    body = response.json()
    assert body["price"] == 16.25 and body["category"] == "Specials"
    assert body["name"] == "Kung Pao Chicken" and body["is_available"] is True and body["id"] == 1


def test_admin_can_update_any_restaurants_item(api):
    client, h = api
    response = client.patch("/restaurants/2/menu/items/4", json={"is_available": False}, headers=h["admin"])
    assert response.status_code == 200 and response.json()["is_available"] is False


def test_patch_cannot_deactivate_an_item(api):
    client, h = api
    response = client.patch("/restaurants/1/menu/items/1", json={"is_active": False}, headers=h["owner1"])
    assert response.status_code == 200 and response.json()["is_active"] is True
    assert 1 in menu_ids(client)


@pytest.mark.parametrize("body", [{"price": 0}, {"price": -1}, {"price": "cheap"}, {"is_available": "maybe"}, {"name": ""}])
def test_invalid_patch_returns_422_and_changes_nothing(app_data, body):
    client, h = app_data.client, app_data.headers
    before = stored_items(app_data)
    response = client.patch("/restaurants/1/menu/items/1", json=body, headers=h["owner1"])
    assert response.status_code == 422
    assert stored_items(app_data) == before


# ---- DELETE: soft delete (#87) ----

def test_delete_returns_204_and_keeps_the_item_stored_as_inactive(app_data):
    client, h = app_data.client, app_data.headers
    before = stored_items(app_data)
    response = client.delete("/restaurants/1/menu/items/1", headers=h["owner1"])
    assert response.status_code == 204 and response.content == b""

    after = stored_items(app_data)
    assert len(after) == len(before)  # never removed from menus.json
    item = next(i for i in after if i["id"] == 1)
    assert item["is_active"] is False
    assert item["name"] == "Kung Pao Chicken" and item["price"] == 15.5  # nothing else changed
    assert [i for i in after if i["id"] != 1] == [i for i in before if i["id"] != 1]


def test_deactivated_items_are_hidden_from_the_customer_menu(api):
    client, h = api
    assert menu_ids(client) == [1, 2, 3]
    client.delete("/restaurants/1/menu/items/1", headers=h["owner1"])
    assert menu_ids(client) == [2, 3]  # item 3 is unavailable, not deactivated, so it stays
    assert 1 not in menu_ids(client, 2)


def test_deactivated_items_cannot_be_added_to_a_cart(api):
    client, h = api
    client.delete("/restaurants/1/menu/items/1", headers=h["owner1"])
    response = add_to_cart(client, h["customer"], 1)
    assert response.status_code == 409 and "not available" in response.json()["detail"]


def test_deactivating_an_item_already_in_a_cart_marks_the_line_unavailable(api):
    client, h = api
    add_to_cart(client, h["customer"], 1)
    client.delete("/restaurants/1/menu/items/1", headers=h["owner1"])
    cart = client.get("/cart", headers=h["customer"]).json()
    assert cart["items"][0]["menu_item_id"] == 1  # the cart still refers to its ID
    assert cart["items"][0]["is_available"] is False
    assert client.post("/checkout", headers=h["customer"]).status_code == 409


def test_a_past_order_keeps_working_after_its_item_is_deactivated(api):
    client, h = api
    add_to_cart(client, h["customer"], 1)
    order = client.post("/checkout", headers=h["customer"]).json()
    client.delete("/restaurants/1/menu/items/1", headers=h["owner1"])
    again = client.get(f"/orders/{order['id']}", headers=h["customer"])
    assert again.status_code == 200 and again.json()["items"][0]["name"] == "Kung Pao Chicken"


def test_deleting_twice_still_returns_204(api):
    client, h = api
    assert client.delete("/restaurants/1/menu/items/1", headers=h["owner1"]).status_code == 204
    assert client.delete("/restaurants/1/menu/items/1", headers=h["owner1"]).status_code == 204


def test_admin_can_deactivate_any_restaurants_item(api):
    client, h = api
    assert client.delete("/restaurants/2/menu/items/4", headers=h["admin"]).status_code == 204
    assert 4 not in menu_ids(client, 2)


# ---- 404 ----

@pytest.mark.parametrize("method", ["patch", "delete"])
def test_unknown_item_returns_404(api, method):
    client, h = api
    kwargs = {"json": {"price": 5}} if method == "patch" else {}
    response = getattr(client, method)("/restaurants/1/menu/items/999", headers=h["owner1"], **kwargs)
    assert response.status_code == 404 and "999" in response.json()["detail"]


@pytest.mark.parametrize("method", ["patch", "delete"])
def test_item_of_another_restaurant_returns_404(api, method):
    client, h = api
    kwargs = {"json": {"price": 5}} if method == "patch" else {}
    response = getattr(client, method)("/restaurants/1/menu/items/4", headers=h["owner1"], **kwargs)
    assert response.status_code == 404


@pytest.mark.parametrize("method", ["patch", "delete"])
def test_unknown_restaurant_returns_404_for_an_admin(api, method):
    client, h = api
    kwargs = {"json": {"price": 5}} if method == "patch" else {}
    assert getattr(client, method)("/restaurants/99/menu/items/1", headers=h["admin"], **kwargs).status_code == 404


# ---- 401 / 403 ----

@pytest.mark.parametrize("method", ["patch", "delete"])
def test_no_token_returns_401(api, method):
    client, _ = api
    kwargs = {"json": {"price": 5}} if method == "patch" else {}
    assert getattr(client, method)("/restaurants/1/menu/items/1", **kwargs).status_code == 401


@pytest.mark.parametrize("who", ["customer", "owner2", "deactivated"])
@pytest.mark.parametrize("method", ["patch", "delete"])
def test_only_the_restaurants_owner_or_an_admin_can_change_it(app_data, method, who):
    client, h = app_data.client, app_data.headers
    before = stored_items(app_data)
    kwargs = {"json": {"price": 5}} if method == "patch" else {}
    response = getattr(client, method)("/restaurants/1/menu/items/1", headers=h[who], **kwargs)
    assert response.status_code == 403
    assert stored_items(app_data) == before


@pytest.mark.parametrize("method", ["patch", "delete"])
def test_non_admin_gets_403_not_404_for_an_unknown_restaurant(api, method):
    client, h = api
    kwargs = {"json": {"price": 5}} if method == "patch" else {}
    assert getattr(client, method)("/restaurants/99/menu/items/1", headers=h["owner1"], **kwargs).status_code == 403


def test_non_integer_ids_return_422(api):
    client, h = api
    assert client.delete("/restaurants/1/menu/items/abc", headers=h["owner1"]).status_code == 422
    assert client.patch("/restaurants/abc/menu/items/1", json={}, headers=h["owner1"]).status_code == 422


# ---- documentation ----

def test_item_routes_are_documented(app_data):
    paths = app_data.client.get("/openapi.json").json()["paths"]["/restaurants/{restaurant_id}/menu/items/{item_id}"]
    patch, delete = paths["patch"], paths["delete"]
    assert patch["summary"] == "Update a menu item" and delete["summary"] == "Deactivate a menu item"
    assert {"200", "401", "403", "404", "422", "500"} <= patch["responses"].keys()
    assert {"204", "401", "403", "404", "422", "500"} <= delete["responses"].keys()
    assert all(p["description"] for p in patch["parameters"] + delete["parameters"])
