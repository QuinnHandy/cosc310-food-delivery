import secrets
from datetime import datetime, timezone

from app.core.security import hash_password, verify_password
from app.repositories.session_repository import SessionRepository
from app.repositories.user_repository import UserNotFoundError, UserRepository
from app.schemas.auth import LoginResponse, Session
from app.schemas.user import User

# Hash of a random value nobody knows. Checked when an email has no account.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(32))


class InvalidCredentialsError(Exception):
    """Raised when an email, password or session token is not valid."""


class AccountDeactivatedError(Exception):
    """Raised when the right password is given for a deactivated account."""


class AuthService:
    """Sign-in and sign-out rules. Does no file access of its own."""

    def __init__(
        self, user_repository: UserRepository, session_repository: SessionRepository
    ) -> None:
        self._user_repository = user_repository
        self._session_repository = session_repository

    def login(self, email: str, password: str) -> LoginResponse:
        """Raises InvalidCredentialsError or AccountDeactivatedError if sign-in is refused."""
        user = self._user_repository.get_by_email(email)
        # An unknown email still costs one hash, so response time does not reveal it.
        stored_hash = user.password_hash if user is not None else _DUMMY_HASH
        password_matches = verify_password(password, stored_hash)
        # Same message for both cases, so a caller cannot tell which emails are registered.
        if user is None or not password_matches:
            raise InvalidCredentialsError("Invalid email or password")
        # Checked only after the password, so only the account holder learns it is deactivated.
        if not user.is_active:
            raise AccountDeactivatedError("This account has been deactivated")

        session = Session(
            token=secrets.token_urlsafe(32),
            user_id=user.id,
            created_at=datetime.now(timezone.utc),
        )
        self._session_repository.add(session)
        return LoginResponse(token=session.token, user_id=user.id, role=user.role)

    def get_user_for_token(self, token: str) -> User:
        """Returns the user a session token belongs to.

        Raises InvalidCredentialsError if the token is not a current session (or its user no
        longer exists), and AccountDeactivatedError if the user has been deactivated since.
        """
        session = self._session_repository.get(token)
        if session is None:
            raise InvalidCredentialsError("Invalid session token")
        try:
            user = self._user_repository.get(session.user_id)
        except UserNotFoundError as exc:
            raise InvalidCredentialsError("Invalid session token") from exc
        if not user.is_active:
            raise AccountDeactivatedError("This account has been deactivated")
        return user

    def logout(self, token: str) -> None:
        """Raises InvalidCredentialsError if the token is not a current session."""
        if not self._session_repository.delete(token):
            raise InvalidCredentialsError("Invalid session token")
