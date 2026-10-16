from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_home_page_is_served():   # to check that FASTAPI returns html page
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Restaurants" in response.text


def test_static_script_is_served():  # to confirm that the JavaScript file is reachable at the HTML URL
    response = client.get("/static/app.js")
    assert response.status_code == 200
    assert "/restaurants" in response.text


def test_unknown_static_file_returns_404(): # failure case to check that missing file returns 404 instead of crashing
    response = client.get("/static/does-not-exist.js")
    assert response.status_code == 404

def test_home_page_has_search_controls():
    html = client.get("/").text
    assert 'id="search-name"' in html
    assert 'id="search-cuisine"' in html
    assert 'id="search-clear"' in html


def test_script_sends_search_filters_to_api():
    script = client.get("/static/app.js").text
    assert 'params.set("name"' in script
    assert 'params.set("cuisine"' in script


def test_search_api_used_by_page_returns_empty_list_for_no_match():
    response = client.get("/restaurants", params={"name": "zzz-no-such-place"})
    assert response.status_code == 200
    assert response.json() == []