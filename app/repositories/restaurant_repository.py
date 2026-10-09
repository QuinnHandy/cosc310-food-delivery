import json, os, tempfile

from pathlib import Path

from pydantic import ValidationError

from app.schemas.restaurant import Restaurant, RestaurantCreate, RestaurantUpdate

class DataAccessError(Exception):
    """Raised when restaurant data cannot be read or parsed."""


class RestaurantNotFoundError(Exception):
    """Raised when a restaurant ID does not exist."""


def write_json_atomic(path: Path, records: list[dict]) -> None:
    """Write records to a temp file, then swap it in, so a crash never leaves a half-written file."""
    path = Path(path)
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
        ) as tmp:
            json.dump(records, tmp, indent=2)
            tmp.write("\n")
            tmp_name = tmp.name
        os.replace(tmp_name, path)
    except OSError as exc:
        raise DataAccessError(f"Could not write data file: {path}") from exc
    

class RestaurantRepository:
    """Reads restaurants from a JSON file. The only layer that touches the file."""

    def __init__(self, data_file: Path) -> None:
        self._data_file = Path(data_file)

    def list_all(self) -> list[Restaurant]:
        try:
            raw = self._data_file.read_text(encoding="utf-8")
        except OSError as exc:
            raise DataAccessError(
                f"Could not read restaurant data file: {self._data_file}"
            ) from exc

        try:
            records = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise DataAccessError(
                f"Restaurant data file is not valid JSON: {self._data_file}"
            ) from exc

        if not isinstance(records, list):
            raise DataAccessError(
                f"Restaurant data file must contain a JSON list: {self._data_file}"
            )

        try:
            return [Restaurant.model_validate(record) for record in records]
        except ValidationError as exc:
            raise DataAccessError(
                f"Restaurant record does not match the Restaurant model: {exc}"
            ) from exc
    def get(self, restaurant_id: int) -> Restaurant:
        for restaurant in self.list_all():
            if restaurant.id == restaurant_id:
                return restaurant
        raise RestaurantNotFoundError(f"Restaurant {restaurant_id} not found")

    def add(self, new: RestaurantCreate) -> Restaurant:
        restaurants = self.list_all()
        next_id = max((r.id for r in restaurants), default=0) + 1
        restaurant = Restaurant(id=next_id, **new.model_dump())
        write_json_atomic(
            self._data_file, [r.model_dump() for r in [*restaurants, restaurant]]
        )
        return restaurant

    def update(self, restaurant_id: int, changes: RestaurantUpdate) -> Restaurant:
        restaurants = self.list_all()
        for index, existing in enumerate(restaurants):
            if existing.id == restaurant_id:
                merged = {**existing.model_dump(), **changes.model_dump(exclude_unset=True)}
                restaurants[index] = Restaurant.model_validate(merged)
                write_json_atomic(self._data_file, [r.model_dump() for r in restaurants])
                return restaurants[index]
        raise RestaurantNotFoundError(f"Restaurant {restaurant_id} not found")