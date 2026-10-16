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