import json
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.api.routes.restaurants import get_restaurant_repository
from app.main import app
from app.repositories.restaurant_repository import (
    RestaurantNotFoundError,
    RestaurantRepository,
)
from app.schemas.restaurant import Restaurant
from app.services.restaurant_service import RestaurantService

TEST_DATA = [
    {"id": 1, "name": "Test Pizza", "cuisine": "Italian"},
    {"id": 2, "name": "Test Sushi", "cuisine": "Japanese"},
]


# Points the app at a temporary data file so tests never touch data/restaurants.json.
@pytest.fixture
def client(tmp_path):
    data_file = tmp_path / "restaurants.json"
    data_file.write_text(json.dumps(TEST_DATA), encoding="utf-8")
    app.dependency_overrides[get_restaurant_repository] = lambda: RestaurantRepository(data_file)
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_restaurant_returns_details(client):
    response = client.get("/restaurants/2")
    assert response.status_code == 200
    assert response.json() == {"id": 2, "name": "Test Sushi", "cuisine": "Japanese"}


def test_get_restaurant_unknown_id_returns_404(client):
    response = client.get("/restaurants/99")
    assert response.status_code == 404
    assert response.json() == {"detail": "Restaurant 99 not found"}


def test_get_restaurant_non_integer_id_returns_422(client):
    response = client.get("/restaurants/abc")
    assert response.status_code == 422


def test_service_get_restaurant_returns_repository_result():
    repository = Mock(spec=RestaurantRepository)
    repository.get.return_value = Restaurant(id=1, name="Test Pizza", cuisine="Italian")

    restaurant = RestaurantService(repository).get_restaurant(1)

    repository.get.assert_called_once_with(1)
    assert restaurant.name == "Test Pizza"


def test_service_get_restaurant_unknown_id_raises():
    repository = Mock(spec=RestaurantRepository)
    repository.get.side_effect = RestaurantNotFoundError("Restaurant 99 not found")

    with pytest.raises(RestaurantNotFoundError):
        RestaurantService(repository).get_restaurant(99)
