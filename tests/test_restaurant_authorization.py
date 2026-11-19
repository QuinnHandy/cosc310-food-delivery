"""Who may change restaurants and menus (#82). All data lives in tmp_path.

Seeded users (see auth_helpers.py): admin; owner1 owns restaurant 1; owner2 owns restaurant 2;
a customer; and a deactivated customer.
"""

import json

import pytest
from auth_helpers import auth  # noqa: F401  (pytest fixture)
from fastapi.testclient import TestClient

from app.api.routes import menus, restaurants
from app.main import app
from app.repositories.menu_repository import MenuRepository
from app.repositories.restaurant_repository import RestaurantRepository

RESTAURANTS = [
    {"id": 1, "name": "Golden Dragon", "cuisine": "Chinese"},
    {"id": 2, "name": "Spice Garden", "cuisine": "Indian"},
]
MENU = [
    {
        "id": 1,
        "restaurant_id": 1,
        "name": "Fried Rice",
        "description": "",
        "price": 9.5,
        "category": "Mains",
        "is_available": True,
        "image_url": "",
    }
]
NEW_RESTAURANT = {"name": "Pizza Palace", "cuisine": "Italian"}
NEW_ITEM = {"name": "Spring Rolls", "price": 6.0, "category": "Starters"}
DENIED_RESPONSE = {"detail": "You do not have permission to change this restaurant"}


@pytest.fixture
def env(tmp_path, auth):
    restaurants_file = tmp_path / "restaurants.json"
    menus_file = tmp_path / "menus.json"
    restaurants_file.write_text(json.dumps(RESTAURANTS), encoding="utf-8")
    menus_file.write_text(json.dumps(MENU), encoding="utf-8")

    def restaurant_repository():
        return RestaurantRepository(restaurants_file)

    def menu_repository():
        return MenuRepository(menus_file, restaurant_repository())

    app.dependency_overrides[restaurants.get_restaurant_repository] = restaurant_repository
    app.dependency_overrides[restaurants.get_menu_repository] = menu_repository
    app.dependency_overrides[menus.get_menu_repository] = menu_repository
    try:
        yield TestClient(app), restaurants_file, menus_file
    finally:
        app.dependency_overrides.pop(restaurants.get_restaurant_repository, None)
        app.dependency_overrides.pop(restaurants.get_menu_repository, None)
        app.dependency_overrides.pop(menus.get_menu_repository, None)


def saved(path):
    return json.loads(path.read_text(encoding="utf-8"))


# --- POST /restaurants ----------------------------------------------------------------------


@pytest.mark.parametrize("who", ["owner1", "owner2", "admin"])
def test_owner_or_admin_can_create_a_restaurant(env, auth, who):
    client, restaurants_file, _ = env

    response = client.post("/restaurants", json=NEW_RESTAURANT, headers=auth[who])

    assert response.status_code == 201
    assert saved(restaurants_file)[-1] == response.json()


# Failure case: no token.
def test_create_restaurant_without_token_gives_401(env):
    client, restaurants_file, _ = env

    response = client.post("/restaurants", json=NEW_RESTAURANT)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert saved(restaurants_file) == RESTAURANTS


# Failure case: a token that was never issued.
def test_create_restaurant_with_unknown_token_gives_401(env):
    client, restaurants_file, _ = env

    response = client.post(
        "/restaurants", json=NEW_RESTAURANT, headers={"Authorization": "Bearer nope"}
    )

    assert response.status_code == 401
    assert saved(restaurants_file) == RESTAURANTS


# Failure case: a customer, and a deactivated account, are both refused.
@pytest.mark.parametrize("who", ["customer", "deactivated"])
def test_create_restaurant_as_customer_gives_403(env, auth, who):
    client, restaurants_file, _ = env

    response = client.post("/restaurants", json=NEW_RESTAURANT, headers=auth[who])

    assert response.status_code == 403
    assert saved(restaurants_file) == RESTAURANTS


# Failure case: the sign-in check comes before body validation.
def test_create_restaurant_without_token_is_401_even_with_a_bad_body(env):
    client, *_ = env

    assert client.post("/restaurants", json={"name": "", "cuisine": ""}).status_code == 401


# --- PATCH /restaurants/{id} ----------------------------------------------------------------


@pytest.mark.parametrize("who", ["owner1", "admin"])
def test_owner_of_that_restaurant_or_admin_can_update_it(env, auth, who):
    client, restaurants_file, _ = env

    response = client.patch("/restaurants/1", json={"name": "Renamed"}, headers=auth[who])

    assert response.status_code == 200
    assert saved(restaurants_file)[0]["name"] == "Renamed"


def test_admin_can_update_any_restaurant(env, auth):
    client, *_ = env

    assert client.patch("/restaurants/2", json={"name": "X"}, headers=auth["admin"]).status_code == 200


# Failure case: no token.
def test_update_restaurant_without_token_gives_401(env):
    client, restaurants_file, _ = env

    response = client.patch("/restaurants/1", json={"name": "Hacked"})

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert saved(restaurants_file) == RESTAURANTS


# Failure case: another restaurant's owner, a customer, and a deactivated account.
@pytest.mark.parametrize("who", ["owner2", "customer", "deactivated"])
def test_update_restaurant_by_someone_else_gives_403(env, auth, who):
    client, restaurants_file, _ = env

    response = client.patch("/restaurants/1", json={"name": "Hacked"}, headers=auth[who])

    assert response.status_code == 403
    assert saved(restaurants_file) == RESTAURANTS


def test_update_403_says_the_restaurant_is_not_theirs(env, auth):
    client, *_ = env

    response = client.patch("/restaurants/1", json={"name": "Hacked"}, headers=auth["owner2"])

    assert response.json() == DENIED_RESPONSE


# Failure case: a non-admin gets 403, not 404, so they cannot probe which IDs exist.
def test_unknown_restaurant_is_403_for_an_owner_and_404_for_an_admin(env, auth):
    client, *_ = env

    owner = client.patch("/restaurants/999", json={"name": "X"}, headers=auth["owner1"])
    admin = client.patch("/restaurants/999", json={"name": "X"}, headers=auth["admin"])

    assert owner.status_code == 403
    assert admin.status_code == 404


# --- POST /restaurants/{id}/menu ------------------------------------------------------------


@pytest.mark.parametrize("who", ["owner1", "admin"])
def test_owner_of_that_restaurant_or_admin_can_add_a_menu_item(env, auth, who):
    client, _, menus_file = env

    response = client.post("/restaurants/1/menu", json=NEW_ITEM, headers=auth[who])

    assert response.status_code == 201
    assert saved(menus_file)[-1] == response.json()


# Failure case: no token.
def test_add_menu_item_without_token_gives_401(env):
    client, _, menus_file = env

    response = client.post("/restaurants/1/menu", json=NEW_ITEM)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert saved(menus_file) == MENU


# Failure case: another restaurant's owner, a customer, and a deactivated account.
@pytest.mark.parametrize("who", ["owner2", "customer", "deactivated"])
def test_add_menu_item_by_someone_else_gives_403(env, auth, who):
    client, _, menus_file = env

    response = client.post("/restaurants/1/menu", json=NEW_ITEM, headers=auth[who])

    assert response.status_code == 403
    assert saved(menus_file) == MENU


# Failure case: the owner check uses the restaurant in the URL, not the one in the body or menu.
def test_owner_cannot_add_to_another_restaurants_menu(env, auth):
    client, _, menus_file = env

    response = client.post("/restaurants/2/menu", json=NEW_ITEM, headers=auth["owner1"])

    assert response.status_code == 403
    assert saved(menus_file) == MENU


# --- Public reads stay open -----------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/restaurants",
        "/restaurants?name=gold",
        "/restaurants?cuisine=indian",
        "/restaurants/1",
        "/restaurants/1/menu",
    ],
)
def test_public_reads_work_without_a_token(env, path):
    client, *_ = env

    response = client.get(path)

    assert response.status_code == 200


def test_public_reads_return_the_data(env):
    client, *_ = env

    assert [r["id"] for r in client.get("/restaurants").json()] == [1, 2]
    assert client.get("/restaurants/1/menu").json()["items"][0]["name"] == "Fried Rice"
