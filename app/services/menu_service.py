from app.repositories.menu_repository import MenuRepository
from app.schemas.menu import Menu, MenuItem, MenuItemCreate


class MenuService:
    """Business logic for menus. Does no file access of its own."""

    def __init__(self, repository: MenuRepository) -> None:
        self._repository = repository

    def get_menu(self, restaurant_id: int) -> Menu:
        """Raises RestaurantNotFoundError if no restaurant has this ID."""
        return self._repository.get_menu(restaurant_id)

    def add_menu_item(self, restaurant_id: int, new: MenuItemCreate) -> MenuItem:
        """Raises RestaurantNotFoundError if no restaurant has this ID."""
        return self._repository.add_item(restaurant_id, new)