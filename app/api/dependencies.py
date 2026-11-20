"""Shared FastAPI dependencies for signing in and reading the caller's token."""

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.repositories.restaurant_repository import RestaurantRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService

bearer_scheme = HTTPBearer(auto_error=False, description="Token from POST /auth/login")


def get_user_repository() -> UserRepository:
    restaurant_repository = RestaurantRepository(settings.data_dir / "restaurants.json")
    return UserRepository(settings.data_dir / "users.json", restaurant_repository)


def get_session_repository() -> SessionRepository:
    return SessionRepository(settings.data_dir / "sessions.json")


def get_auth_service(
    user_repository: UserRepository = Depends(get_user_repository),
    session_repository: SessionRepository = Depends(get_session_repository),
) -> AuthService:
    return AuthService(user_repository, session_repository)


def get_bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    """Returns the token from the Authorization header, or responds with 401."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials
