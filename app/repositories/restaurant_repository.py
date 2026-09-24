import json
from pathlib import Path

from pydantic import ValidationError

from app.schemas.restaurant import Restaurant


class DataAccessError(Exception):
    """Raised when restaurant data cannot be read or parsed."""


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
