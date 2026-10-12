from app.repositories.restaurant_repository import RestaurantRepository
from app.schemas.restaurant import Restaurant


class RestaurantService:
    """Business logic for restaurants. Does no file access of its own."""

    def __init__(self, repository: RestaurantRepository) -> None:
        self._repository = repository

    def list_restaurants(self) -> list[Restaurant]:
        restaurants = self._repository.list_all()
        return sorted(restaurants, key=lambda restaurant: restaurant.id)

    def get_restaurant(self, restaurant_id: int) -> Restaurant:
        """Raises RestaurantNotFoundError if no restaurant has this ID."""
        return self._repository.get(restaurant_id)
