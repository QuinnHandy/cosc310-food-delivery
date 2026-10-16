
import json

import pytest
from fastapi.testclient import TestClient

from app.api.routes.restaurants import get_restaurant_repository
from app.main import app
from app.repositories.restaurant_repository import RestaurantRepository


@pytest.fixture
def client(tmp_path):
    data_file = tmp_path / "restaurants.json"
    data_file.write_text(
        json.dumps([
            {"id": 1, "name": "Pizza Place", "cuisine": "Italian"}
        ]),
        encoding="utf-8",
    )

    def test_repository():
        return RestaurantRepository(data_file)

    app.dependency_overrides[get_restaurant_repository] = test_repository

    try:
        yield TestClient(app), data_file
    finally:
        app.dependency_overrides.pop(get_restaurant_repository, None)


def test_update_restaurant(client):
    test_client, data_file = client

    response = test_client.patch(
        "/restaurants/1",
        json={"name": "New Pizza Place"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "name": "New Pizza Place",
        "cuisine": "Italian",
    }

    saved_data = json.loads(data_file.read_text(encoding="utf-8"))
    assert saved_data[0] == response.json()

    # Verify a fresh repository instance can read the saved update.
    repository = RestaurantRepository(data_file)
    assert repository.get(1).name == "New Pizza Place"


def test_update_unknown_restaurant(client):
    test_client, _ = client

    response = test_client.patch(
        "/restaurants/999",
        json={"name": "Unknown Restaurant"},
    )

    assert response.status_code == 404


def test_update_invalid_input(client):
    test_client, _ = client

    response = test_client.patch(
        "/restaurants/1",
        json={"name": ""},
    )

    assert response.status_code == 422


def test_update_preserves_id(client):
    test_client, _ = client

    response = test_client.patch(
        "/restaurants/1",
        json={"cuisine": "Japanese"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["name"] == "Pizza Place"
    assert response.json()["cuisine"] == "Japanese"
