from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_home_page_is_served():   # to check that FASTAPI returns html page
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Restaurants" in response.text


def test_static_scripts_are_served():  # the JavaScript files must be reachable at the URLs the pages use
    for path in ("/static/api.js", "/static/app.js", "/static/owner.js"):
        response = client.get(path)
        assert response.status_code == 200, path


def test_unknown_static_file_returns_404():  # failure case: missing file returns 404 instead of crashing
    response = client.get("/static/does-not-exist.js")
    assert response.status_code == 404


def test_home_page_has_search_controls():
    html = client.get("/").text
    assert 'id="search-name"' in html
    assert 'id="search-cuisine"' in html
    assert 'id="search-clear"' in html


def test_api_script_sends_search_filters_to_api():
    script = client.get("/static/api.js").text
    assert "/restaurants" in script
    assert 'params.set("name"' in script
    assert 'params.set("cuisine"' in script


def test_search_api_used_by_page_returns_empty_list_for_no_match():
    response = client.get("/restaurants", params={"name": "zzz-no-such-place"})
    assert response.status_code == 200
    assert response.json() == []


def test_owner_page_is_served():
    response = client.get("/owner")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert 'id="manage-form"' in response.text
    assert 'href="/"' in response.text  # link back to the customer page


def test_customer_page_links_to_owner_page_but_has_no_form():
    html = client.get("/").text
    assert 'href="/owner"' in html
    assert 'id="manage-form"' not in html


def test_api_script_uses_create_and_update_endpoints():
    script = client.get("/static/api.js").text
    assert 'method: "POST"' in script
    assert 'method: "PATCH"' in script