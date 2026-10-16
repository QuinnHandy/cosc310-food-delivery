from app.repositories.menu_repository import MenuRepository
from app.schemas.menu import MenuItem, MenuItemCreate


class MenuService:
    """Business logic for menu items. Does no file access."""

    def __init__(self, repository: MenuRepository) -> None:
        self._repository = repository

    def add_menu_item(
        self, restaurant_id: int, new: MenuItemCreate
    ) -> MenuItem:
        return self._repository.add_item(restaurant_id, new)
