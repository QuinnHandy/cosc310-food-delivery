import json

import pytest

from app.repositories.restaurant_repository import DataAccessError, RestaurantRepository


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