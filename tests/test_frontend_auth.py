"""Sign-in, register and sign-out on the web pages (#97).

These check what is served. The behaviour (token saved, header sent, 401 redirect, API
messages shown) is checked by tests/js/account.test.js through tests/test_frontend_js.py.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_account_page_is_served_with_both_forms():
    response = client.get("/account")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    for element_id in ("signin-form", "signin-email", "signin-password",
                       "register-form", "register-name", "register-email", "register-password",
                       "register-phone", "register-address"):
        assert f'id="{element_id}"' in response.text, element_id


def test_account_page_is_not_in_the_api_docs():
    assert "/account" not in client.get("/openapi.json").json()["paths"]


def test_account_scripts_are_served():
    for path in ("/static/account.js", "/static/session.js"):
        assert client.get(path).status_code == 200, path


def test_every_page_shows_the_session_bar():
    for page in ("/", "/owner", "/account"):
        html = client.get(page).text
        assert 'id="session-bar"' in html, page
        assert '<script src="/static/session.js">' in html, page
        # api.js must load before the scripts that use it
        assert html.index("/static/api.js") < html.index("/static/session.js"), page


def test_api_script_calls_the_account_endpoints():
    script = client.get("/static/api.js").text
    assert 'request("POST", "/auth/login"' in script
    assert 'request("POST", "/auth/logout"' in script
    assert 'request("POST", "/customers"' in script


def test_api_script_redirects_to_sign_in_on_401():
    script = client.get("/static/api.js").text
    assert "response.status === 401 && auth && redirectOn401" in script
    assert "window.location.href = `/account?${params}`" in script


def test_sign_in_only_follows_same_site_next_links():
    # Behaviour, including "/\\evil.example", is checked in tests/js/account.test.js.
    script = client.get("/static/account.js").text
    assert "new URL(next, window.location.origin)" in script
    assert "url.origin === window.location.origin" in script
    assert 'next.startsWith("/")' not in script  # the old string check that "\\" got around
