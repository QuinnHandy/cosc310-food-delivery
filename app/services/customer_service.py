from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.core.security import hash_password
from app.repositories.user_repository import (
    DuplicateEmailError,
    UserNotFoundError,
    UserRepository,
)
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.schemas.user import User, UserCreateRecord, UserRole, UserUpdate


class CustomerNotFoundError(NotFoundError):
    """Raised when a customer does not exist."""


class EmailAlreadyRegisteredError(ConflictError):
    """Raised when an email is already registered."""


class CustomerAlreadyDeactivatedError(ConflictError):
    """Raised when a customer is already deactivated."""


class CustomerNotAllowedError(ForbiddenError):
    """Raised when the user is not an active customer (deactivated, deleted, or another role)."""


class CustomerService:
    """Customer account rules: register, view, update and deactivate. Does no file access of its own.

    Customers are stored as users with role `customer`. Deactivating never deletes the
    record, so the customer's ID, carts and orders stay valid.
    """

    def __init__(self, user_repository: UserRepository) -> None:
        self._users = user_repository

    def register(self, new: CustomerCreate) -> User:
        """Creates a customer. The role is always `customer` and the password is stored hashed.

        Raises EmailAlreadyRegisteredError if the email is taken.
        """
        record = UserCreateRecord(
            email=new.email,
            password_hash=hash_password(new.password),
            role=UserRole.customer,
            name=new.name,
            phone=new.phone,
            delivery_address=new.delivery_address,
        )
        try:
            return self._users.add(record)
        except DuplicateEmailError as exc:
            raise EmailAlreadyRegisteredError("An account with this email already exists") from exc

    def get_customer(self, customer_id: int) -> User:
        """Raises CustomerNotFoundError if the ID is unknown or is not a customer."""
        try:
            user = self._users.get(customer_id)
        except UserNotFoundError as exc:
            raise CustomerNotFoundError(f"Customer {customer_id} not found") from exc
        if user.role != UserRole.customer:
            raise CustomerNotFoundError(f"Customer {customer_id} not found")
        return user

    def require_active_customer(self, user: User) -> User:
        """The one place that decides whether a user may use a cart or check out (#109).

        Re-reads the account from storage instead of trusting `user`, so a customer who was
        deactivated after signing in is refused even if the caller holds an old User object.
        Returns the current stored customer.

        Raises CustomerNotAllowedError for another role, an unknown account or a deactivated one.
        """
        if user.role != UserRole.customer:
            raise CustomerNotAllowedError("Only customers can use a cart or check out")
        try:
            customer = self.get_customer(user.id)
        except CustomerNotFoundError as exc:
            raise CustomerNotAllowedError("Customer account not found") from exc
        if not customer.is_active:
            raise CustomerNotAllowedError("This account has been deactivated")
        return customer

    def update_customer(self, customer_id: int, changes: CustomerUpdate) -> User:
        """Changes only the fields sent; a field sent as null is treated as left out.

        Raises CustomerNotFoundError for an unknown customer.
        """
        self.get_customer(customer_id)
        update = UserUpdate(**changes.model_dump(exclude_unset=True, exclude_none=True))
        return self._users.update(customer_id, update)

    def deactivate_customer(self, customer_id: int) -> User:
        """Sets is_active to false; the account is kept. Its sessions stop working at once,
        because the auth check rejects deactivated users.

        Raises CustomerNotFoundError, or CustomerAlreadyDeactivatedError if already deactivated.
        """
        customer = self.get_customer(customer_id)
        if not customer.is_active:
            raise CustomerAlreadyDeactivatedError(
                f"Customer {customer_id} is already deactivated"
            )
        return self._users.update(customer_id, UserUpdate(is_active=False))
