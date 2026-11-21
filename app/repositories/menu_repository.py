from pathlib import Path

from app.repositories.json_store import DataAccessError, JsonStore, next_id
from app.repositories.restaurant_repository import RestaurantNotFoundError, RestaurantRepository
from app.schemas.menu import Menu, MenuItem, MenuItemCreate, MenuItemUpdate


class MenuItemNotFoundError(Exception):
    """Raised when a menu item does not exist for the given restaurant."""


class MenuRepository:
    """Reads menu items from a JSON file. Checks every item against the restaurants."""

    def __init__(self, menu_file: Path, restaurant_repository: RestaurantRepository) -> None:
        self._store = JsonStore(menu_file, MenuItem, "menu")
        self._restaurant_repository = restaurant_repository

    def _load_items(self) -> list[MenuItem]:
        items = self._store.load()
        valid_ids = {r.id for r in self._restaurant_repository.list_all()}
        orphans = sorted({i.restaurant_id for i in items if i.restaurant_id not in valid_ids})
        if orphans:
            raise DataAccessError(f"Menu items reference unknown restaurant IDs: {orphans}")
        return items

    def _save_items(self, items: list[MenuItem]) -> None:
        self._store.save(items)

    def get_menu(self, restaurant_id: int) -> Menu:
        self._restaurant_repository.get(restaurant_id)
        items = [i for i in self._load_items() if i.restaurant_id == restaurant_id]
        return Menu(restaurant_id=restaurant_id, items=sorted(items, key=lambda i: i.id))

    def get_item(self, item_id: int) -> MenuItem:
        """Returns a menu item by its ID, whichever restaurant it belongs to.

        Raises MenuItemNotFoundError if no item has this ID.
        """
        for item in self._load_items():
            if item.id == item_id:
                return item
        raise MenuItemNotFoundError(f"Menu item {item_id} not found")

    def add_item(self, restaurant_id: int, new: MenuItemCreate) -> MenuItem:
        self._restaurant_repository.get(restaurant_id)
        items = self._load_items()
        item = MenuItem(id=next_id(items), restaurant_id=restaurant_id, **new.model_dump())
        self._save_items([*items, item])
        return item

    def update_item(self, restaurant_id: int, item_id: int, changes: MenuItemUpdate) -> MenuItem:
        self._restaurant_repository.get(restaurant_id)
        items = self._load_items()
        for index, existing in enumerate(items):
            if existing.id == item_id and existing.restaurant_id == restaurant_id:
                merged = {**existing.model_dump(), **changes.model_dump(exclude_unset=True)}
                items[index] = MenuItem.model_validate(merged)
                self._save_items(items)
                return items[index]
        raise MenuItemNotFoundError(f"Menu item {item_id} not found for restaurant {restaurant_id}")

    def deactivate_item(self, restaurant_id: int, item_id: int) -> MenuItem:
        """Soft delete: sets is_active to false and keeps the item stored, because carts and
        orders refer to its ID. Deactivating an already deactivated item changes nothing.

        Raises RestaurantNotFoundError or MenuItemNotFoundError.
        """
        self._restaurant_repository.get(restaurant_id)
        items = self._load_items()
        for index, existing in enumerate(items):
            if existing.id == item_id and existing.restaurant_id == restaurant_id:
                if existing.is_active:
                    items[index] = existing.model_copy(update={"is_active": False})
                    self._save_items(items)
                return items[index]
        raise MenuItemNotFoundError(f"Menu item {item_id} not found for restaurant {restaurant_id}")
