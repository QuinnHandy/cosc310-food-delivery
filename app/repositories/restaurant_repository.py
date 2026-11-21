from pathlib import Path

from app.core.errors import NotFoundError
from app.repositories.json_store import (  # noqa: F401  (re-exported for existing imports)
    DataAccessError,
    JsonStore,
    next_id,
    write_json_atomic,
)
from app.schemas.restaurant import Restaurant, RestaurantCreate, RestaurantUpdate


class RestaurantNotFoundError(NotFoundError):
    """Raised when a restaurant ID does not exist."""


class RestaurantRepository:
    """Reads and writes restaurants in a JSON file. The only layer that touches the file."""

    def __init__(self, data_file: Path) -> None:
        self._store = JsonStore(data_file, Restaurant, "restaurant")

    def list_all(self) -> list[Restaurant]:
        return self._store.load()

    def get(self, restaurant_id: int) -> Restaurant:
        for restaurant in self.list_all():
            if restaurant.id == restaurant_id:
                return restaurant
        raise RestaurantNotFoundError(f"Restaurant {restaurant_id} not found")

    def add(self, new: RestaurantCreate) -> Restaurant:
        restaurants = self.list_all()
        restaurant = Restaurant(id=next_id(restaurants), **new.model_dump())
        self._store.save([*restaurants, restaurant])
        return restaurant

    def update(self, restaurant_id: int, changes: RestaurantUpdate) -> Restaurant:
        restaurants = self.list_all()
        for index, existing in enumerate(restaurants):
            if existing.id == restaurant_id:
                merged = {**existing.model_dump(), **changes.model_dump(exclude_unset=True)}
                restaurants[index] = Restaurant.model_validate(merged)
                self._store.save(restaurants)
                return restaurants[index]
        raise RestaurantNotFoundError(f"Restaurant {restaurant_id} not found")
