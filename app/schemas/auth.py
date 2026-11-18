from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.user import UserRole


class LoginRequest(BaseModel):
    """Request body for signing in."""

    email: str = Field(description="Account email. Upper or lower case both work.")
    password: str = Field(min_length=1, description="Account password. Must not be empty.")


class LoginResponse(BaseModel):
    """Returned after a successful sign in."""

    token: str = Field(description="Send this as 'Authorization: Bearer <token>'.")
    user_id: int = Field(description="ID of the signed-in user.")
    role: UserRole = Field(description="Role of the signed-in user.")


class Session(BaseModel):
    """A signed-in session as stored in data/sessions.json."""

    token: str = Field(description="Random token that identifies this session.")
    user_id: int = Field(description="ID of the user this session belongs to.")
    created_at: datetime = Field(description="When the session was created (UTC).")


class MessageResponse(BaseModel):
    """A short confirmation message."""

    message: str = Field(description="Human-readable confirmation.")
