"""Shared FastAPI dependencies for signing in, finding out who is calling, and checking roles."""

from collections.abc import Callable

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.openapi import RestaurantId
from app.core.config import settings
from app.repositories.restaurant_repository import DataAccessError, RestaurantRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import User, UserRole
from app.services.customer_service import CustomerService
from app.services.auth_service import (
    AccountDeactivatedError,
    AuthService,
    InvalidCredentialsError,
)

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


def get_customer_service(
    user_repository: UserRepository = Depends(get_user_repository),
) -> CustomerService:
    return CustomerService(user_repository)


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


def get_current_user(
    token: str = Depends(get_bearer_token),
    service: AuthService = Depends(get_auth_service),
) -> User:
    """Returns the signed-in user for the `Authorization: Bearer <token>` header.

    Responds with 401 if the header is missing or malformed, or the token is not a current
    session, and with 403 if the token's user has been deactivated.
    """
    try:
        return service.get_user_for_token(token)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except AccountDeactivatedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except DataAccessError as exc:
        # Fixed message on purpose: DataAccessError text can quote stored user records,
        # including password hashes.
        raise HTTPException(status_code=500, detail="Could not verify the sign-in") from exc


def require_role(*roles: UserRole | str) -> Callable[..., User]:
    """Builds a dependency that returns the signed-in user, or responds with 403 if their role
    is not one of `roles`. Add it to a route with `Depends(require_role("admin"))`.

    Includes everything `get_current_user` checks, so a missing or invalid token is still 401.
    """
    allowed = frozenset(UserRole(role) for role in roles)  # a typo in a role fails at import
    if not allowed:
        raise ValueError("require_role needs at least one role")

    def check_role(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=403, detail="You do not have permission to do this"
            )
        return user

    return check_role


def require_restaurant_access(
    restaurant_id: RestaurantId,
    user: User = Depends(get_current_user),
) -> User:
    """Lets an admin, or the owner of this restaurant (`user.restaurant_id == restaurant_id`),
    through. Anyone else who is signed in gets 403. Use it on any route with a `restaurant_id`
    path parameter that changes that restaurant or its menu.

    Includes everything `get_current_user` checks, so a missing or invalid token is still 401.
    This never looks the restaurant up, so a non-admin gets 403 for an ID that does not exist
    (an admin gets the route's own 404), and a non-admin cannot tell which IDs exist.
    """
    is_admin = user.role == UserRole.admin
    owns_restaurant = user.role == UserRole.restaurant_owner and user.restaurant_id == restaurant_id
    if not (is_admin or owns_restaurant):
        raise HTTPException(
            status_code=403, detail="You do not have permission to change this restaurant"
        )
    return user
