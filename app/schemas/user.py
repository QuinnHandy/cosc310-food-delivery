from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class UserRole(str, Enum):
    """What a user is allowed to do in the app."""

    customer = "customer"
    restaurant_owner = "restaurant_owner"
    admin = "admin"


def _normalise_email(value: str) -> str:
    """Lowercase and strip an email, and reject anything that is clearly not an email."""
    email = value.strip().lower()
    local, at, domain = email.partition("@")
    if not local or not at or "@" in domain or "." not in domain:
        raise ValueError("Email must contain exactly one '@' with a '.' after it.")
    return email


class _UserFields(BaseModel):
    """Fields shared by a stored user and a new user. Not used directly."""

    email: str = Field(
        description="Login email. Stored lowercase and must be unique across all users."
    )
    password_hash: str = Field(
        description="Hashed password (pbkdf2_sha256$iterations$salt$hash). Never a plain password."
    )
    role: UserRole = Field(description="'customer', 'restaurant_owner' or 'admin'.")
    name: str = Field(min_length=1, description="Display name. Must not be empty.")
    phone: str = Field(default="", description="Phone number. Optional.")
    delivery_address: str = Field(
        default="", description="Default delivery address for customers. Optional."
    )
    is_active: bool = Field(
        default=True, description="False means the account is deactivated and cannot log in."
    )
    restaurant_id: int | None = Field(
        default=None,
        description="ID of the restaurant this user manages. Required for owners, null otherwise.",
    )

    @field_validator("email")
    @classmethod
    def _check_email(cls, value: str) -> str:
        return _normalise_email(value)

    @model_validator(mode="after")
    def _check_owner_restaurant(self) -> "_UserFields":
        if self.role == UserRole.restaurant_owner and self.restaurant_id is None:
            raise ValueError("A restaurant_owner must have a restaurant_id.")
        if self.role != UserRole.restaurant_owner and self.restaurant_id is not None:
            raise ValueError("Only a restaurant_owner can have a restaurant_id.")
        return self


class User(_UserFields):
    """A user as stored in data/users.json. Includes the password hash, so never return it from the API."""

    id: int = Field(description="Server-assigned unique ID. Never changes and is never reused.")


class UserCreateRecord(_UserFields):
    """A new user for the repository to store. The ID is assigned by the repository.

    The password must already be hashed (see app.core.security.hash_password).
    """


class UserUpdate(BaseModel):
    """Partial update for a user. Leave a field out to keep its current value.

    The ID, email, role and restaurant ID cannot be changed.
    """

    name: str | None = Field(
        default=None, min_length=1, description="New display name. Must not be empty if sent."
    )
    phone: str | None = Field(default=None, description="New phone number.")
    delivery_address: str | None = Field(default=None, description="New delivery address.")
    is_active: bool | None = Field(
        default=None, description="Set to false to deactivate the account."
    )
    password_hash: str | None = Field(
        default=None, description="New hashed password. Never a plain password."
    )


class UserPublic(BaseModel):
    """A user as returned by the API. Everything in User except the password hash."""

    id: int = Field(description="Server-assigned unique ID. Never changes and is never reused.")
    email: str = Field(description="Login email, lowercase.")
    role: UserRole = Field(description="'customer', 'restaurant_owner' or 'admin'.")
    name: str = Field(description="Display name.")
    phone: str = Field(description="Phone number. Empty if not set.")
    delivery_address: str = Field(description="Default delivery address. Empty if not set.")
    is_active: bool = Field(description="False means the account is deactivated.")
    restaurant_id: int | None = Field(
        description="ID of the restaurant this user manages. Null unless the user is an owner."
    )
