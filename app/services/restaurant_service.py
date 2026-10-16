from app.repositories.restaurant_repository import RestaurantRepository
from app.schemas.restaurant import Restaurant


class RestaurantService:
    """Business logic for restaurants. Does no file access of its own."""

    def __init__(self, repository: RestaurantRepository) -> None:
        self._repository = repository

    def search_restaurants(
        self, name: str | None = None, cuisine: str | None = None
    ) -> list[Restaurant]:
        restaurants = self._repository.list_all()
        name = name.strip().lower() if name else ""
        cuisine = cuisine.strip().lower() if cuisine else ""
        if name:
            restaurants = [r for r in restaurants if name in r.name.lower()]
        if cuisine:
            restaurants = [r for r in restaurants if r.cuisine.lower() == cuisine]
        return sorted(restaurants, key=lambda r: r.id)

    def get_restaurant(self, restaurant_id: int) -> Restaurant:
        """Raises RestaurantNotFoundError if no restaurant has this ID."""
        return self._repository.get(restaurant_id)
