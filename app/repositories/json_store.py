"""Shared JSON-file storage for the repositories (#108).

Every repository used to repeat the same steps: read the file, parse JSON, check it is a
list, validate each record with a Pydantic model, write it back atomically, and work out the
next ID. `JsonStore` does those steps once, so each repository keeps only its own rules
(which records belong together, what "not found" means, cross-file references).
"""

import json
import os
import tempfile
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import BaseModel, ValidationError


class DataAccessError(Exception):
    """Raised when stored data cannot be read, parsed, validated or written."""


Model = TypeVar("Model", bound=BaseModel)


def write_json_atomic(path: Path, records: list[dict]) -> None:
    """Writes records to a temp file in the same folder, then swaps it in with os.replace.

    The records are serialized before the temp file is created, so a record that can't be
    turned into JSON fails without touching anything, and a crash mid-write never leaves a
    half-written data file.
    """
    path = Path(path)
    try:
        text = json.dumps(records, indent=2) + "\n"
    except (TypeError, ValueError) as exc:
        raise DataAccessError(f"Could not serialize data for {path}: {exc}") from exc
    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
        ) as tmp:
            tmp_name = tmp.name
            tmp.write(text)
        os.replace(tmp_name, path)
    except OSError as exc:
        if tmp_name is not None and os.path.exists(tmp_name):
            os.remove(tmp_name)
        raise DataAccessError(f"Could not write data file: {path}") from exc


def next_id(records: Iterable[BaseModel]) -> int:
    """The ID for a new record: one more than the largest existing ID (1 for none).

    IDs of removed or closed records are never handed out again.
    """
    return max((record.id for record in records), default=0) + 1


class JsonStore(Generic[Model]):
    """A JSON file holding a list of one kind of Pydantic model.

    `label` names the data in error messages ("Restaurant data file is not valid JSON").
    With `missing_ok`, a file that doesn't exist yet reads as an empty list, for data the
    app creates at runtime (sessions, carts); otherwise it is a DataAccessError.
    """

    def __init__(
        self,
        path: Path,
        model: type[Model],
        label: str,
        *,
        missing_ok: bool = False,
        dump: Callable[[Model], dict] | None = None,
    ) -> None:
        self.path = Path(path)
        self._model = model
        self._label = label
        self._missing_ok = missing_ok
        self._dump = dump or (lambda record: record.model_dump(mode="json"))

    def load(self) -> list[Model]:
        """Reads and validates every record. Raises DataAccessError if anything is wrong."""
        try:
            raw = self.path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            if self._missing_ok:
                return []
            raise DataAccessError(f"Could not read {self._label} data file: {self.path}") from exc
        except OSError as exc:
            raise DataAccessError(f"Could not read {self._label} data file: {self.path}") from exc

        try:
            records = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise DataAccessError(
                f"{self._label.capitalize()} data file is not valid JSON: {self.path}"
            ) from exc

        if not isinstance(records, list):
            raise DataAccessError(
                f"{self._label.capitalize()} data file must contain a JSON list: {self.path}"
            )

        try:
            return [self._model.model_validate(record) for record in records]
        except ValidationError as exc:
            raise DataAccessError(
                f"{self._label.capitalize()} record does not match the "
                f"{self._model.__name__} model: {exc}"
            ) from exc

    def save(self, records: list[Model]) -> None:
        """Writes every record atomically (see write_json_atomic)."""
        write_json_atomic(self.path, [self._dump(record) for record in records])

    def require_unique_ids(self, records: list[Model]) -> None:
        """Raises DataAccessError if two records share an ID."""
        ids = [record.id for record in records]
        if len(ids) != len(set(ids)):
            raise DataAccessError(
                f"{self._label.capitalize()} data file contains duplicate IDs: {self.path}"
            )
