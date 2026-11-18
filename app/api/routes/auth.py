from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_auth_service, get_bearer_token
from app.api.openapi import FORBIDDEN, UNAUTHORIZED, data_error
from app.repositories.restaurant_repository import DataAccessError
from app.schemas.auth import LoginRequest, LoginResponse, MessageResponse
from app.services.auth_service import (
    AccountDeactivatedError,
    AuthService,
    InvalidCredentialsError,
)

router = APIRouter()


# The 500 messages below are fixed on purpose: DataAccessError text can quote stored
# user records, including password hashes, and these routes are open to anyone.
@router.post(
    "/auth/login",
    response_model=LoginResponse,
    status_code=200,
    tags=["auth"],
    summary="Sign in",
    responses={
        **UNAUTHORIZED,
        **FORBIDDEN,
        **data_error("Stored user or session data could not be read or saved."),
    },
)
def login(
    credentials: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    """Checks the email and password and returns a new session token.

    Returns `401` with the same message for an unknown email or a wrong password, `403` if the password is right but the account is deactivated, and `422` if `email` or `password` is missing or `password` is empty.
    """
    try:
        return service.login(credentials.email, credentials.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except AccountDeactivatedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except DataAccessError as exc:
        raise HTTPException(status_code=500, detail="Could not complete sign in") from exc


@router.post(
    "/auth/logout",
    response_model=MessageResponse,
    status_code=200,
    tags=["auth"],
    summary="Sign out",
    responses={
        **UNAUTHORIZED,
        **data_error("Stored session data could not be read or saved."),
    },
)
def logout(
    token: str = Depends(get_bearer_token),
    service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    """Deletes the session for the token in the `Authorization: Bearer <token>` header, so the token stops working.

    Returns `401` if the header is missing or the token is not a current session.
    """
    try:
        service.logout(token)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except DataAccessError as exc:
        raise HTTPException(status_code=500, detail="Could not complete sign out") from exc
    return MessageResponse(message="Signed out")
