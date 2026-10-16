import json

import pytest

from app.repositories.restaurant_repository import (
    DataAccessError,
    RestaurantNotFoundError,
    RestaurantRepository,
)


# Tests successful loading of restaurant data from temporary JSON.
def test_repository_loads_restaurants(tmp_path):
    test_data = [
        {
            "id": 1,
            "name": "Test Pizza",
            "cuisine": "Italian"
        },
        {
            "id": 2,
            "name": "Test Sushi",
            "cuisine": "Japanese"
        }
    ]

    data_file = tmp_path / "restaurants.json"
    data_file.write_text(json.dumps(test_data), encoding="utf-8")

    repository = RestaurantRepository(data_file)

    restaurants = repository.list_all()

    assert len(restaurants) == 2
    assert restaurants[0].id == 1
    assert restaurants[0].name == "Test Pizza"
    assert restaurants[0].cuisine == "Italian"
    assert restaurants[1].id == 2



# Tests repository failure handling for invalid JSON data.
def test_repository_rejects_invalid_json(tmp_path):
    data_file = tmp_path / "restaurants.json"
    data_file.write_text("not valid json", encoding="utf-8")

    repository = RestaurantRepository(data_file)

    with pytest.raises(DataAccessError):
        repository.list_all()


# Tests looking up a single restaurant by ID.
def test_repository_get_returns_matching_restaurant(tmp_path):
    test_data = [
        {"id": 2, "name": "Test Sushi", "cuisine": "Japanese"},
        {"id": 1, "name": "Test Pizza", "cuisine": "Italian"},
    ]
    data_file = tmp_path / "restaurants.json"
    data_file.write_text(json.dumps(test_data), encoding="utf-8")

    restaurant = RestaurantRepository(data_file).get(1)

    assert restaurant.id == 1
    assert restaurant.name == "Test Pizza"
    assert restaurant.cuisine == "Italian"


# Tests that looking up an unknown ID raises a not-found error.
def test_repository_get_unknown_id_raises(tmp_path):
    data_file = tmp_path / "restaurants.json"
    data_file.write_text(json.dumps([]), encoding="utf-8")

    with pytest.raises(RestaurantNotFoundError, match="Restaurant 99 not found"):
        RestaurantRepository(data_file).get(99)