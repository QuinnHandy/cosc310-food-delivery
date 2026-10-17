from fastapi.testclient import TestClient

from app.api.routes.restaurants import get_restaurant_repository
from app.main import app
from app.repositories.restaurant_repository import RestaurantRepository


def test_create_then_update_then_get_restaurant(tmp_path):
    data_file = tmp_path / "restaurants.json"
    data_file.write_text("[]", encoding="utf-8")
    app.dependency_overrides[get_restaurant_repository] = lambda: RestaurantRepository(data_file)

    try:
        client = TestClient(app)

        created = client.post("/restaurants", json={"name": "Test Thai", "cuisine": "Thai"})
        assert created.status_code == 201
        restaurant_id = created.json()["id"]

        updated = client.patch(f"/restaurants/{restaurant_id}", json={"cuisine": "Vietnamese"})
        assert updated.status_code == 200

        fetched = client.get(f"/restaurants/{restaurant_id}")
        assert fetched.status_code == 200
        assert fetched.json() == {"id": restaurant_id, "name": "Test Thai", "cuisine": "Vietnamese"}
    finally:
        app.dependency_overrides.clear()