"""Checkout, orders page and profile on the web pages (#99).

These check what is served. Behaviour is checked in tests/js/checkout.test.js,
orders.test.js, profile.test.js and flow.test.js (the whole register → order flow),
run by tests/test_frontend_js.py.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_customer_page_has_checkout_and_confirmation():
    html = client.get("/").text
    for element_id in ("cart-checkout", "checkout-status", "order-confirmation", "order-confirmation-body"):
        assert f'id="{element_id}"' in html, element_id
    assert html.index("/static/cart.js") < html.index("/static/order-view.js") < html.index("/static/checkout.js")


def test_orders_page_is_served_and_hidden_from_docs():
    response = client.get("/orders")
    assert response.status_code == 200
    assert 'id="orders-list"' in response.text and 'id="order-detail"' in response.text
    assert "/orders" not in client.get("/openapi.json").json()["paths"]


def test_account_page_has_profile_form():
    html = client.get("/account").text
    for element_id in ("profile-section", "profile-name", "profile-phone", "profile-address", "profile-form"):
        assert f'id="{element_id}"' in html, element_id


def test_new_scripts_are_served():
    for path in ("/static/checkout.js", "/static/order-view.js", "/static/orders.js"):
        assert client.get(path).status_code == 200, path


def test_api_script_calls_checkout_order_and_profile_endpoints_with_the_token():
    script = client.get("/static/api.js").text
    section = script[script.index("// ---- Checkout and orders"):]
    for call in ('request("POST", "/checkout"', 'request("GET", "/customers/me/orders"',
                 'request("GET", `/orders/${orderId}`', 'request("GET", "/customers/me"',
                 'request("PATCH", "/customers/me"'):
        assert call in section, call
    assert section.count("auth: true") == 5


def test_order_view_shows_the_stored_snapshot_without_recalculating():
    script = client.get("/static/order-view.js").text
    for field in ("order.id", "order.status", "line.line_total", "order.subtotal", "order.delivery_fee", "order.total"):
        assert field in script, field
    assert "*" not in script.replace("/*", "").replace("*/", "")  # no multiplication
