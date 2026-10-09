import json

import pytest

from app.repositories.restaurant_repository import (
    DataAccessError,
    RestaurantNotFoundError,
    RestaurantRepository,
)
from app.schemas.restaurant import RestaurantCreate, RestaurantUpdate


def make_repo(tmp_path, records):
    data_file = tmp_path / "restaurants.json"
    data_file.write_text(json.dumps(records), encoding="utf-8")
    return RestaurantRepository(data_file), data_file


EXISTING = [
    {"id": 3, "name": "Test Pizza", "cuisine": "Italian"},
    {"id": 1, "name": "Test Sushi", "cuisine": "Japanese"},
]


# New IDs are max + 1 and existing records are untouched.
def test_add_generates_new_id_without_changing_existing(tmp_path):
    repo, _ = make_repo(tmp_path, EXISTING)

    created = repo.add(RestaurantCreate(name="New Place", cuisine="Thai"))

    assert created.id == 4
    saved = {r.id: r for r in repo.list_all()}
    assert saved[3].name == "Test Pizza"
    assert saved[1].name == "Test Sushi"
    assert len(saved) == 3


# First record in an empty file gets ID 1.
def test_add_to_empty_file_starts_at_one(tmp_path):
    repo, _ = make_repo(tmp_path, [])

    assert repo.add(RestaurantCreate(name="First", cuisine="Thai")).id == 1


# Data written survives a "restart" (a brand-new repository instance) and is valid JSON.
def test_added_data_loads_after_restart(tmp_path):
    repo, data_file = make_repo(tmp_path, EXISTING)
    repo.add(RestaurantCreate(name="New Place", cuisine="Thai"))

    restarted = RestaurantRepository(data_file)

    assert [r.name for r in restarted.list_all()] == ["Test Pizza", "Test Sushi", "New Place"]
    json.loads(data_file.read_text(encoding="utf-8"))
    assert list(tmp_path.glob("*.tmp")) == []


# Partial update changes only the fields sent and never the ID.
def test_update_changes_only_sent_fields(tmp_path):
    repo, data_file = make_repo(tmp_path, EXISTING)

    updated = repo.update(1, RestaurantUpdate(cuisine="Sushi Bar"))

    assert updated.id == 1
    assert updated.name == "Test Sushi"
    assert updated.cuisine == "Sushi Bar"
    assert RestaurantRepository(data_file).get(1).cuisine == "Sushi Bar"


# Failure case: updating a restaurant that does not exist.
def test_update_unknown_restaurant_raises(tmp_path):
    repo, _ = make_repo(tmp_path, EXISTING)

    with pytest.raises(RestaurantNotFoundError):
        repo.update(99, RestaurantUpdate(name="Nope"))


# Failure case: unwritable location surfaces as DataAccessError and leaves the original intact.
def test_add_write_failure_raises_and_keeps_original(tmp_path):
    repo, data_file = make_repo(tmp_path, EXISTING)
    original = data_file.read_text(encoding="utf-8")
    broken = RestaurantRepository(tmp_path / "missing_dir" / "restaurants.json")

    with pytest.raises(DataAccessError):
        broken.add(RestaurantCreate(name="X", cuisine="Y"))
    assert data_file.read_text(encoding="utf-8") == original