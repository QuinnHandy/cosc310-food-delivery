from app.repositories.menu_repository import MenuRepository
from app.schemas.menu import Menu, MenuItem, MenuItemCreate, MenuItemUpdate


class MenuService:
    """Business logic for menus. Does no file access of its own."""

    def __init__(self, repository: MenuRepository) -> None:
        self._repository = repository

    def get_menu(self, restaurant_id: int) -> Menu:
        """The menu customers see: deactivated items (#87) are hidden. Unavailable items are
        kept and shown as unavailable.

        Raises RestaurantNotFoundError if no restaurant has this ID.
        """
        menu = self._repository.get_menu(restaurant_id)
        visible = [item for item in menu.items if item.is_active]
        return Menu(restaurant_id=menu.restaurant_id, items=visible)

    def add_menu_item(self, restaurant_id: int, new: MenuItemCreate) -> MenuItem:
        """Raises RestaurantNotFoundError if no restaurant has this ID."""
        return self._repository.add_item(restaurant_id, new)

    def update_menu_item(
        self, restaurant_id: int, item_id: int, changes: MenuItemUpdate
    ) -> MenuItem:
        """Changes only the fields sent. Sending `is_available` false or true makes the item
        temporarily unavailable or available again. Deactivating is a separate action
        (deactivate_menu_item), so `is_active` cannot be changed here.

        Raises RestaurantNotFoundError or MenuItemNotFoundError.
        """
        return self._repository.update_item(restaurant_id, item_id, changes)

    def deactivate_menu_item(self, restaurant_id: int, item_id: int) -> None:
        """Soft delete (#87): the item stays stored so carts and orders that refer to its ID keep
        working, but it is hidden from the customer menu and cannot be added to a cart.

        Raises RestaurantNotFoundError or MenuItemNotFoundError.
        """
        self._repository.deactivate_item(restaurant_id, item_id)
