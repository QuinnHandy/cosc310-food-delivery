"""API models for customer accounts (#83-#86). Stored customers are `User` records with
role `customer` (see app/schemas/user.py)."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.user import _normalise_email

MIN_PASSWORD_LENGTH = 8


class CustomerCreate(BaseModel):
    """Request body for registering a customer. The role is always `customer`; it cannot be sent."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, description="Display name. Must not be empty.")
    email: str = Field(description="Login email. Must be unique; stored lowercase.")
    password: str = Field(
        min_length=MIN_PASSWORD_LENGTH,
        description=f"Plain password, at least {MIN_PASSWORD_LENGTH} characters. Stored only as a hash.",
    )
    phone: str = Field(default="", description="Phone number. Optional.")
    delivery_address: str = Field(default="", description="Default delivery address. Optional.")

    @field_validator("name", "phone", "delivery_address")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, value: str) -> str:
        if not value:
            raise ValueError("Name must not be empty.")
        return value

    @field_validator("email")
    @classmethod
    def _check_email(cls, value: str) -> str:
        return _normalise_email(value)


class CustomerUpdate(BaseModel):
    """Partial update of the signed-in customer. Leave a field out (or send null) to keep its value.

    Any other field (such as `email`, `role`, `id` or `is_active`) is rejected with 422.
    """

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, description="New display name. Must not be empty if sent.")
    phone: str | None = Field(default=None, description="New phone number. May be empty.")
    delivery_address: str | None = Field(
        default=None, description="New delivery address. Must not be empty if sent."
    )

    @field_validator("name", "phone", "delivery_address")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("name", "delivery_address")
    @classmethod
    def _not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("Must not be empty.")
        return value


class CustomerResponse(BaseModel):
    """A customer as returned by the API. Never includes the password or its hash."""

    id: int = Field(description="Server-assigned unique ID. Never changes and is never reused.")
    email: str = Field(description="Login email, lowercase.")
    name: str = Field(description="Display name.")
    phone: str = Field(description="Phone number. Empty if not set.")
    delivery_address: str = Field(description="Default delivery address. Empty if not set.")
    is_active: bool = Field(description="False means the account is deactivated.")
