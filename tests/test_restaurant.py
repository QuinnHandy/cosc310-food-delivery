from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_restaurants_endpoint():
    response = client.get("/restaurants")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2

    first = data[0]
    assert "id" in first
    assert "name" in first
    assert "cuisine" in first
    assert isinstance(first["id"], int)
    assert isinstance(first["name"], str)
    assert isinstance(first["cuisine"], str)

def test_restaurants_invalid_path():
    response = client.get("/restaurant")  # wrong path
    assert response.status_code == 404
