import json
from pathlib import Path

from pydantic import ValidationError

from app.repositories.restaurant_repository import (
    DataAccessError,
    RestaurantRepository,
    write_json_atomic,
)
from app.schemas.user import User, UserCreateRecord, UserRole, UserUpdate


class UserNotFoundError(Exception):
    """Raised when a user ID does not exist."""


class DuplicateEmailError(Exception):
    """Raised when a user with the same email already exists."""


class UserRepository:
    """Reads and writes users in a JSON file. Checks owners against the restaurants.

    Only handles password hashes, never plain passwords.
    """

    def __init__(self, user_file: Path, restaurant_repository: RestaurantRepository) -> None:
        self._user_file = Path(user_file)
        self._restaurant_repository = restaurant_repository

    def list_all(self) -> list[User]:
        try:
            raw = self._user_file.read_text(encoding="utf-8")
        except OSError as exc:
            raise DataAccessError(f"Could not read user data file: {self._user_file}") from exc

        try:
            records = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise DataAccessError(f"User data file is not valid JSON: {self._user_file}") from exc

        if not isinstance(records, list):
            raise DataAccessError(f"User data file must contain a JSON list: {self._user_file}")

        try:
            users = [User.model_validate(record) for record in records]
        except ValidationError as exc:
            raise DataAccessError(f"User record does not match the User model: {exc}") from exc

        ids = [u.id for u in users]
        if len(ids) != len(set(ids)):
            raise DataAccessError(f"User data file contains duplicate user IDs: {self._user_file}")
        emails = [u.email for u in users]
        if len(emails) != len(set(emails)):
            raise DataAccessError(f"User data file contains duplicate emails: {self._user_file}")

        valid_ids = {r.id for r in self._restaurant_repository.list_all()}
        orphans = sorted(
            {
                u.restaurant_id
                for u in users
                if u.restaurant_id is not None and u.restaurant_id not in valid_ids
            }
        )
        if orphans:
            raise DataAccessError(f"Users reference unknown restaurant IDs: {orphans}")
        return users

    def _save(self, users: list[User]) -> None:
        # Write "id" first so the file stays easy to read.
        write_json_atomic(
            self._user_file,
            [{"id": u.id, **u.model_dump(mode="json", exclude={"id"})} for u in users],
        )

    def get(self, user_id: int) -> User:
        for user in self.list_all():
            if user.id == user_id:
                return user
        raise UserNotFoundError(f"User {user_id} not found")

    def get_by_email(self, email: str) -> User | None:
        wanted = email.strip().lower()
        for user in self.list_all():
            if user.email == wanted:
                return user
        return None

    def add(self, new: UserCreateRecord) -> User:
        users = self.list_all()
        if any(u.email == new.email for u in users):
            raise DuplicateEmailError(f"A user with email {new.email} already exists")
        if new.role == UserRole.restaurant_owner:
            self._restaurant_repository.get(new.restaurant_id)
        next_id = max((u.id for u in users), default=0) + 1
        user = User(id=next_id, **new.model_dump())
        self._save([*users, user])
        return user

    def update(self, user_id: int, changes: UserUpdate) -> User:
        users = self.list_all()
        for index, existing in enumerate(users):
            if existing.id == user_id:
                merged = {**existing.model_dump(), **changes.model_dump(exclude_unset=True)}
                users[index] = User.model_validate(merged)
                self._save(users)
                return users[index]
        raise UserNotFoundError(f"User {user_id} not found")
