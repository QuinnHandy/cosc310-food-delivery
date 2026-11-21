"""Cart panel on the customer page (#98).

These check what is served; tests/js/cart.test.js (run by test_frontend_js.py) checks the
behaviour: requests sent, totals shown exactly as the API returns them, and API errors shown.
"""

import re

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_customer_page_has_a_cart_panel():
    html = client.get("/").text
    for element_id in ("cart", "cart-status", "cart-list", "cart-subtotal",
                       "cart-delivery-fee", "cart-total", "cart-clear"):
        assert f'id="{element_id}"' in html, element_id


def test_cart_script_is_served_and_loaded_in_order():
    assert client.get("/static/cart.js").status_code == 200
    html = client.get("/").text
    assert html.index("/static/api.js") < html.index("/static/cart.js") < html.index("/static/app.js")


def test_api_script_has_every_cart_call_with_the_token():
    script = client.get("/static/api.js").text
    for call in ('request("GET", "/cart"', 'request("POST", "/cart/items"',
                 'request("PATCH", `/cart/items/${menuItemId}`',
                 'request("DELETE", `/cart/items/${menuItemId}`', 'request("DELETE", "/cart/items"'):
        assert call in script, call
    cart_section = script[script.index("// ---- Cart"):].split("// ---- Checkout")[0]
    assert cart_section.count("auth: true") == 5


def test_cart_script_never_calculates_totals():
    script = client.get("/static/cart.js").text
    # Totals are only ever read from the API response, never summed or multiplied in JS.
    assert "cart.subtotal" in script and "cart.total" in script and "line.line_total" in script
    assert not re.search(r"(unit_price|price)\s*\*", script)
    assert ".reduce(" not in script


def test_add_to_cart_buttons_are_on_menu_items():
    script = client.get("/static/app.js").text
    assert '"Add to cart"' in script
    assert "CartPanel.add(menuItem)" in script
    assert "add.disabled = !menuItem.is_available" in script
