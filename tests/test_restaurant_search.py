import json
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.api.routes.restaurants import get_restaurant_repository
from app.main import app
from app.repositories.restaurant_repository import RestaurantRepository
from app.schemas.restaurant import Restaurant
from app.services.restaurant_service import RestaurantService

TEST_DATA = [
    {"id": 1, "name": "Pizza Place", "cuisine": "Italian"},
    {"id": 2, "name": "Sushi Spot", "cuisine": "Japanese"},
    {"id": 3, "name": "Pasta Palace", "cuisine": "Italian"},
    {"id": 4, "name": "Pizza Tokyo", "cuisine": "Japanese"},
]


# Points the app at a temporary data file so tests never touch data/restaurants.json.
@pytest.fixture
def client(tmp_path):
    data_file = tmp_path / "restaurants.json"
    data_file.write_text(json.dumps(TEST_DATA), encoding="utf-8")
    app.dependency_overrides[get_restaurant_repository] = lambda: RestaurantRepository(data_file)
    yield TestClient(app)
    app.dependency_overrides.clear()


def ids(response):
    return [r["id"] for r in response.json()]


# --- Route tests ---

def test_search_no_params_returns_full_list(client):
    response = client.get("/restaurants")
    assert response.status_code == 200
    assert ids(response) == [1, 2, 3, 4]


def test_search_name_partial_match_ignores_case(client):
    response = client.get("/restaurants", params={"name": "PIZ"})
    assert response.status_code == 200
    assert ids(response) == [1, 4]


def test_search_cuisine_keeps_only_matching_cuisine(client):
    response = client.get("/restaurants", params={"cuisine": "italian"})
    assert response.status_code == 200
    assert ids(response) == [1, 3]


def test_search_name_and_cuisine_together_narrow_results(client):
    response = client.get("/restaurants", params={"name": "pizza", "cuisine": "Japanese"})
    assert response.status_code == 200
    assert ids(response) == [4]


# Failure case: no matches is an empty list, not a 404.
def test_search_no_matches_returns_200_and_empty_list(client):
    response = client.get("/restaurants", params={"name": "zzz"})
    assert response.status_code == 200
    assert response.json() == []


# Edge case: cuisine must match exactly, so a partial cuisine finds nothing.
def test_search_partial_cuisine_returns_empty_list(client):
    response = client.get("/restaurants", params={"cuisine": "ital"})
    assert response.status_code == 200
    assert response.json() == []


# Edge case: empty or whitespace-only parameters are ignored.
@pytest.mark.parametrize("params", [
    {"name": ""},
    {"name": "   "},
    {"cuisine": ""},
    {"cuisine": "   "},
    {"name": " ", "cuisine": ""},
])
def test_search_blank_params_return_full_list(client, params):
    response = client.get("/restaurants", params=params)
    assert response.status_code == 200
    assert ids(response) == [1, 2, 3, 4]


# --- Service unit tests (repository mocked, no route or file involved) ---

@pytest.fixture
def service():
    repository = Mock(spec=RestaurantRepository)
    repository.list_all.return_value = [Restaurant(**r) for r in reversed(TEST_DATA)]
    return RestaurantService(repository)


def names(restaurants):
    return [r.name for r in restaurants]


def test_service_search_no_filters_returns_all_sorted_by_id(service):
    assert [r.id for r in service.search_restaurants()] == [1, 2, 3, 4]


def test_service_search_name_is_partial_and_case_insensitive(service):
    assert names(service.search_restaurants(name="pIzZa")) == ["Pizza Place", "Pizza Tokyo"]


def test_service_search_cuisine_is_exact_and_case_insensitive(service):
    assert names(service.search_restaurants(cuisine="JAPANESE")) == ["Sushi Spot", "Pizza Tokyo"]
    assert service.search_restaurants(cuisine="Japan") == []


def test_service_search_requires_both_filters_to_match(service):
    assert names(service.search_restaurants(name="pa", cuisine="italian")) == ["Pasta Palace"]


def test_service_search_trims_spaces(service):
    assert names(service.search_restaurants(name="  sushi  ", cuisine=" japanese ")) == ["Sushi Spot"]


def test_service_search_no_matches_returns_empty_list(service):
    assert service.search_restaurants(name="zzz") == []


@pytest.mark.parametrize("blank", [None, "", "   "])
def test_service_search_blank_filters_are_ignored(service, blank):
    assert len(service.search_restaurants(name=blank, cuisine=blank)) == 4
