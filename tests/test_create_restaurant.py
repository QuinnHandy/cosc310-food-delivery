import json

from fastapi.testclient import TestClient

from app.api.routes.restaurants import get_restaurant_repository
from app.main import app
from app.repositories.restaurant_repository import RestaurantRepository


def test_create_restaurant(tmp_path):
    # Create isolated test data
    data_file = tmp_path / "restaurants.json"
    data_file.write_text("[]", encoding="utf-8")

    # Override the repository dependency to use test data
    def test_repository():
        return RestaurantRepository(data_file)

    app.dependency_overrides[get_restaurant_repository] = test_repository

    try:
        client = TestClient(app)

        response = client.post(
            "/restaurants",
            json={"name": "Pizza Palace", "cuisine": "Italian"},
        )

        assert response.status_code == 201

        restaurant = response.json()

        assert restaurant["id"] == 1
        assert restaurant["name"] == "Pizza Palace"
        assert restaurant["cuisine"] == "Italian"

        # Verify the restaurant was saved to JSON
        saved_data = json.loads(data_file.read_text(encoding="utf-8"))

        assert len(saved_data) == 1
        assert saved_data[0] == restaurant

    finally:
        app.dependency_overrides.clear()

def test_create_restaurant_empty_name():
    client = TestClient(app)

    response = client.post(
        "/restaurants",
        json={"name": "", "cuisine": "Italian"},
    )

    assert response.status_code == 422