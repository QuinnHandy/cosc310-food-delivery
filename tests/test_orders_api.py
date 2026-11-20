"""GET /customers/me/orders, GET /customers/{id}/orders (#96) and GET /orders/{id} (#95) through HTTP, on temporary data."""

import pytest

from app.repositories.order_repository import OrderRepository
from app_data_helpers import app_data  # noqa: F401  (pytest fixture)
from test_order_service import make_draft


@pytest.fixture
def api(app_data):
    return app_data.client, app_data.headers


def seed_orders(app_data, *customer_ids):
    repo = OrderRepository(app_data.data_dir / "orders.json")
    return [repo.add(make_draft(customer_id=cid)) for cid in customer_ids]


# ---- GET /customers/me/orders ----


def test_my_orders_returns_200_with_only_my_orders_newest_first(app_data):
    client, h = app_data.client, app_data.headers
    seed_orders(app_data, 4, 5, 4, 5, 4)  # IDs 1..5; Alice (4) owns 1, 3, 5
    response = client.get("/customers/me/orders", headers=h["customer"])
    assert response.status_code == 200
    orders = response.json()
    assert [o["id"] for o in orders] == [5, 3, 1]
    assert {o["customer_id"] for o in orders} == {4}


def test_my_orders_use_the_full_order_shape(app_data):
    client, h = app_data.client, app_data.headers
    seed_orders(app_data, 4)
    order = client.get("/customers/me/orders", headers=h["customer"]).json()[0]
    assert order["restaurant_name"] == "Golden Dragon"
    assert order["items"][0]["name"] == "Kung Pao Chicken"
    assert (order["subtotal"], order["delivery_fee"], order["total"]) == (31.0, 4.99, 35.99)
    assert order["status"] == "placed" and "created_at" in order


def test_other_customers_orders_never_show_up(app_data):
    client, h = app_data.client, app_data.headers
    seed_orders(app_data, 5, 5)
    assert client.get("/customers/me/orders", headers=h["customer"]).json() == []
    assert len(client.get("/customers/me/orders", headers=h["customer2"]).json()) == 2


def test_no_orders_returns_200_and_an_empty_list_not_404(app_data):
    client, h = app_data.client, app_data.headers
    response = client.get("/customers/me/orders", headers=h["customer"])
    assert response.status_code == 200
    assert response.json() == []


def test_missing_orders_file_still_returns_an_empty_list(app_data):
    (app_data.data_dir / "orders.json").unlink()
    response = app_data.client.get("/customers/me/orders", headers=app_data.headers["customer"])
    assert response.status_code == 200 and response.json() == []


def test_my_orders_without_a_token_returns_401(api):
    client, _ = api
    response = client.get("/customers/me/orders")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_my_orders_with_a_bad_token_returns_401(api):
    client, _ = api
    response = client.get("/customers/me/orders", headers={"Authorization": "Bearer nope"})
    assert response.status_code == 401


@pytest.mark.parametrize("who", ["owner1", "admin", "deactivated"])
def test_my_orders_is_for_active_customers_only(api, who):
    client, h = api
    assert client.get("/customers/me/orders", headers=h[who]).status_code == 403


def test_me_is_not_read_as_a_customer_id(api):
    """Route order: /customers/me/orders must not fall into /customers/{customer_id}/orders."""
    client, h = api
    assert client.get("/customers/me/orders", headers=h["customer"]).status_code == 200
    assert client.get("/customers/me/orders", headers=h["admin"]).status_code == 403  # not 422


def test_checkout_then_list_shows_the_new_order_first(api):
    client, h = api
    for quantity in (1, 3):
        client.post("/cart/items", json={"menu_item_id": 1, "quantity": quantity}, headers=h["customer"])
        assert client.post("/checkout", headers=h["customer"]).status_code == 201
    orders = client.get("/customers/me/orders", headers=h["customer"]).json()
    assert [o["id"] for o in orders] == [2, 1]
    assert orders[0]["items"][0]["quantity"] == 3


def test_listing_orders_changes_no_files(app_data):
    seed_orders(app_data, 4)
    before = {p.name: p.read_bytes() for p in app_data.data_dir.glob("*.json")}
    app_data.client.get("/customers/me/orders", headers=app_data.headers["customer"])
    app_data.client.get("/customers/4/orders", headers=app_data.headers["admin"])
    after = {p.name: p.read_bytes() for p in app_data.data_dir.glob("*.json")}
    assert before == after


def test_unreadable_order_data_returns_500_with_a_fixed_message(app_data):
    (app_data.data_dir / "orders.json").write_text("not json", encoding="utf-8")
    response = app_data.client.get("/customers/me/orders", headers=app_data.headers["customer"])
    assert response.status_code == 500
    assert response.json() == {"detail": "Could not access order data"}


# ---- GET /customers/{customer_id}/orders (admin) ----


def test_admin_sees_a_customers_orders_newest_first(app_data):
    client, h = app_data.client, app_data.headers
    seed_orders(app_data, 4, 5, 4)
    response = client.get("/customers/4/orders", headers=h["admin"])
    assert response.status_code == 200
    assert [o["id"] for o in response.json()] == [3, 1]


def test_admin_gets_an_empty_list_for_a_customer_with_no_orders(app_data):
    response = app_data.client.get("/customers/5/orders", headers=app_data.headers["admin"])
    assert response.status_code == 200 and response.json() == []


def test_admin_can_see_a_deactivated_customers_orders(app_data):
    seed_orders(app_data, 6)
    response = app_data.client.get("/customers/6/orders", headers=app_data.headers["admin"])
    assert response.status_code == 200 and len(response.json()) == 1


@pytest.mark.parametrize("customer_id", [99, 1, 2])  # unknown, admin, restaurant owner
def test_unknown_customer_returns_404(app_data, customer_id):
    response = app_data.client.get(f"/customers/{customer_id}/orders", headers=app_data.headers["admin"])
    assert response.status_code == 404
    assert response.json() == {"detail": f"Customer {customer_id} not found"}


def test_admin_lookup_with_a_non_integer_id_returns_422(app_data):
    response = app_data.client.get("/customers/abc/orders", headers=app_data.headers["admin"])
    assert response.status_code == 422


def test_admin_lookup_without_a_token_returns_401(api):
    client, _ = api
    assert client.get("/customers/4/orders").status_code == 401


@pytest.mark.parametrize("who", ["customer", "customer2", "owner1", "deactivated"])
def test_only_admins_can_look_up_a_customers_orders(app_data, who):
    seed_orders(app_data, 4)
    response = app_data.client.get("/customers/4/orders", headers=app_data.headers[who])
    assert response.status_code == 403  # even for the customer's own ID


def test_403_is_checked_before_404(app_data):
    """A non-admin cannot learn which customer IDs exist."""
    response = app_data.client.get("/customers/99/orders", headers=app_data.headers["customer"])
    assert response.status_code == 403


# ---- GET /orders/{order_id} (#95) ----


def test_customer_views_their_own_order(app_data):
    client, h = app_data.client, app_data.headers
    seed_orders(app_data, 4)
    response = client.get("/orders/1", headers=h["customer"])
    assert response.status_code == 200
    order = response.json()
    assert order["id"] == 1 and order["customer_id"] == 4
    assert order["restaurant_name"] == "Golden Dragon"
    assert order["items"][0]["name"] == "Kung Pao Chicken"
    assert (order["subtotal"], order["delivery_fee"], order["total"]) == (31.0, 4.99, 35.99)
    assert order["status"] == "placed" and "created_at" in order


def test_view_order_matches_the_same_order_in_the_list(app_data):
    client, h = app_data.client, app_data.headers
    seed_orders(app_data, 4, 4)
    listed = {o["id"]: o for o in client.get("/customers/me/orders", headers=h["customer"]).json()}
    assert client.get("/orders/2", headers=h["customer"]).json() == listed[2]


def test_viewing_another_customers_order_returns_404_not_403(app_data):
    """403 would confirm the ID exists; 404 looks the same as an unknown ID."""
    client, h = app_data.client, app_data.headers
    seed_orders(app_data, 5)  # Bob's order
    response = client.get("/orders/1", headers=h["customer"])
    assert response.status_code == 404
    assert response.json() == {"detail": "Order 1 not found"}


def test_viewing_an_unknown_order_returns_404(app_data):
    response = app_data.client.get("/orders/99", headers=app_data.headers["customer"])
    assert response.status_code == 404
    assert response.json() == {"detail": "Order 99 not found"}


def test_viewing_an_order_with_no_orders_file_returns_404(app_data):
    (app_data.data_dir / "orders.json").unlink()
    response = app_data.client.get("/orders/1", headers=app_data.headers["customer"])
    assert response.status_code == 404


def test_viewing_an_order_with_a_non_integer_id_returns_422(app_data):
    response = app_data.client.get("/orders/abc", headers=app_data.headers["customer"])
    assert response.status_code == 422


def test_view_order_without_a_token_returns_401(api):
    client, _ = api
    response = client.get("/orders/1")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("who", ["owner1", "admin", "deactivated"])
def test_view_order_is_for_active_customers_only(app_data, who):
    seed_orders(app_data, 4)
    response = app_data.client.get("/orders/1", headers=app_data.headers[who])
    assert response.status_code == 403


def test_checkout_then_view_shows_the_new_order(api):
    client, h = api
    client.post("/cart/items", json={"menu_item_id": 1, "quantity": 2}, headers=h["customer"])
    placed = client.post("/checkout", headers=h["customer"]).json()
    viewed = client.get(f"/orders/{placed['id']}", headers=h["customer"])
    assert viewed.status_code == 200
    assert viewed.json() == placed


def test_viewing_an_order_changes_no_files(app_data):
    seed_orders(app_data, 4)
    before = {p.name: p.read_bytes() for p in app_data.data_dir.glob("*.json")}
    app_data.client.get("/orders/1", headers=app_data.headers["customer"])
    after = {p.name: p.read_bytes() for p in app_data.data_dir.glob("*.json")}
    assert before == after


def test_unreadable_order_data_on_view_returns_500_with_a_fixed_message(app_data):
    (app_data.data_dir / "orders.json").write_text("not json", encoding="utf-8")
    response = app_data.client.get("/orders/1", headers=app_data.headers["customer"])
    assert response.status_code == 500
    assert response.json() == {"detail": "Could not access order data"}
