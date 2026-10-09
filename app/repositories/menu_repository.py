import json
from pathlib import Path

from pydantic import ValidationError

from app.repositories.restaurant_repository import (
    DataAccessError,
    RestaurantRepository,
)
from app.schemas.menu import Menu, MenuItem


class RestaurantNotFoundError(Exception):
    """Raised when a menu is requested for a restaurant that does not exist."""


class MenuRepository:
    """Reads menu items from a JSON file. Checks every item against the restaurants."""

    def __init__(self, menu_file: Path, restaurant_repository: RestaurantRepository) -> None:
        self._menu_file = Path(menu_file)
        self._restaurant_repository = restaurant_repository

    def _load_items(self) -> list[MenuItem]:
        try:
            raw = self._menu_file.read_text(encoding="utf-8")
        except OSError as exc:
            raise DataAccessError(f"Could not read menu data file: {self._menu_file}") from exc

        try:
            records = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise DataAccessError(f"Menu data file is not valid JSON: {self._menu_file}") from exc

        if not isinstance(records, list):
            raise DataAccessError(f"Menu data file must contain a JSON list: {self._menu_file}")

        try:
            items = [MenuItem.model_validate(record) for record in records]
        except ValidationError as exc:
            raise DataAccessError(f"Menu record does not match the MenuItem model: {exc}") from exc

        valid_ids = {r.id for r in self._restaurant_repository.list_all()}
        orphans = sorted({i.restaurant_id for i in items if i.restaurant_id not in valid_ids})
        if orphans:
            raise DataAccessError(f"Menu items reference unknown restaurant IDs: {orphans}")
        return items

    def get_menu(self, restaurant_id: int) -> Menu:
        restaurant_ids = {r.id for r in self._restaurant_repository.list_all()}
        if restaurant_id not in restaurant_ids:
            raise RestaurantNotFoundError(f"Restaurant {restaurant_id} does not exist")
        items = [i for i in self._load_items() if i.restaurant_id == restaurant_id]
        return Menu(restaurant_id=restaurant_id, items=sorted(items, key=lambda i: i.id))