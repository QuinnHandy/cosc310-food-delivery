from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from app.api.dependencies import get_customer_service, require_role
from app.api.openapi import NOT_ALLOWED, NOT_SIGNED_IN, data_error
from app.repositories.restaurant_repository import DataAccessError
from app.schemas.common import ErrorResponse
from app.schemas.customer import CustomerCreate, CustomerResponse, CustomerUpdate
from app.schemas.user import User
from app.services.customer_service import (
    CustomerAlreadyDeactivatedError,
    CustomerNotFoundError,
    CustomerService,
    EmailAlreadyRegisteredError,
)

router = APIRouter(tags=["customers"])

CustomerId = Annotated[int, Path(description="ID of the customer.")]

CUSTOMER_NOT_FOUND = {
    404: {
        "model": ErrorResponse,
        "description": "No customer has this ID (owner and admin IDs count as not found).",
        "content": {"application/json": {"example": {"detail": "Customer 99 not found"}}},
    }
}
EMAIL_TAKEN = {
    409: {
        "model": ErrorResponse,
        "description": "Another account already uses this email.",
        "content": {
            "application/json": {"example": {"detail": "An account with this email already exists"}}
        },
    }
}
ALREADY_DEACTIVATED = {
    409: {
        "model": ErrorResponse,
        "description": "The customer is already deactivated.",
        "content": {
            "application/json": {"example": {"detail": "Customer 6 is already deactivated"}}
        },
    }
}

# Fixed 500 messages: DataAccessError text can quote stored user records, including hashes.
DATA_ERROR = data_error("Stored user data could not be read or saved.")


def _to_response(user: User) -> CustomerResponse:
    return CustomerResponse.model_validate(user.model_dump())


def _data_error(exc: DataAccessError) -> HTTPException:
    return HTTPException(status_code=500, detail="Could not access customer data")


@router.post(
    "/customers",
    response_model=CustomerResponse,
    status_code=201,
    summary="Register a customer",
    responses={**EMAIL_TAKEN, **DATA_ERROR},
)
def register_customer(
    new: CustomerCreate,
    service: CustomerService = Depends(get_customer_service),
) -> CustomerResponse:
    """Creates a customer account and returns it (never the password or hash). Open to anyone; the role is always `customer` and cannot be sent.

    The new customer can sign in at `POST /auth/login` straight away. Returns `409` if the email is already used, and `422` if `name` is empty, the email is not valid, the password is shorter than 8 characters, or an unknown field (such as `role`) is sent.
    """
    try:
        return _to_response(service.register(new))
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except DataAccessError as exc:
        raise _data_error(exc) from exc


@router.get(
    "/customers/me",
    response_model=CustomerResponse,
    summary="View my profile",
    responses={**NOT_SIGNED_IN, **NOT_ALLOWED, **DATA_ERROR},
)
def get_my_profile(user: User = Depends(require_role("customer"))) -> CustomerResponse:
    """Returns the signed-in customer's details and delivery address. Requires a `customer` token.

    Returns `401` without a valid token and `403` for other roles or a deactivated account.
    """
    return _to_response(user)


@router.patch(
    "/customers/me",
    response_model=CustomerResponse,
    summary="Update my details and delivery address",
    responses={**NOT_SIGNED_IN, **NOT_ALLOWED, **DATA_ERROR},
)
def update_my_profile(
    changes: CustomerUpdate,
    user: User = Depends(require_role("customer")),
    service: CustomerService = Depends(get_customer_service),
) -> CustomerResponse:
    """Changes any of `name`, `phone` and `delivery_address`; fields left out (or sent as null) keep their value. The change is saved to `data/users.json`.

    Returns `401` without a valid token, `403` for other roles or a deactivated account, and `422` for an empty `name` or `delivery_address` or any other field (`email`, `role`, `id` and `is_active` cannot be changed here).
    """
    try:
        return _to_response(service.update_customer(user.id, changes))
    except DataAccessError as exc:
        raise _data_error(exc) from exc


@router.post(
    "/customers/me/deactivate",
    response_model=CustomerResponse,
    summary="Deactivate my account",
    responses={**NOT_SIGNED_IN, **NOT_ALLOWED, **DATA_ERROR},
)
def deactivate_my_account(
    user: User = Depends(require_role("customer")),
    service: CustomerService = Depends(get_customer_service),
) -> CustomerResponse:
    """Deactivates the signed-in customer and returns the account with `is_active: false`. The account is kept, not deleted, so its ID and orders stay valid.

    Afterwards, signing in returns `403` and the same token gets `403` on every protected endpoint, including this one (so calling it twice gives `403`). Returns `401` without a valid token and `403` for other roles.
    """
    try:
        return _to_response(service.deactivate_customer(user.id))
    except DataAccessError as exc:
        raise _data_error(exc) from exc


@router.get(
    "/customers/{customer_id}",
    response_model=CustomerResponse,
    summary="View a customer (admin)",
    dependencies=[Depends(require_role("admin"))],
    responses={**NOT_SIGNED_IN, **NOT_ALLOWED, **CUSTOMER_NOT_FOUND, **DATA_ERROR},
)
def get_customer(
    customer_id: CustomerId,
    service: CustomerService = Depends(get_customer_service),
) -> CustomerResponse:
    """Returns any customer by ID. Requires an `admin` token.

    Returns `401` without a valid token, `403` for any other role, `404` if no customer has this ID, and `422` if the ID is not an integer.
    """
    try:
        return _to_response(service.get_customer(customer_id))
    except CustomerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DataAccessError as exc:
        raise _data_error(exc) from exc


@router.post(
    "/customers/{customer_id}/deactivate",
    response_model=CustomerResponse,
    summary="Deactivate a customer (admin)",
    dependencies=[Depends(require_role("admin"))],
    responses={
        **NOT_SIGNED_IN,
        **NOT_ALLOWED,
        **CUSTOMER_NOT_FOUND,
        **ALREADY_DEACTIVATED,
        **DATA_ERROR,
    },
)
def deactivate_customer(
    customer_id: CustomerId,
    service: CustomerService = Depends(get_customer_service),
) -> CustomerResponse:
    """Deactivates any customer by ID and returns the account with `is_active: false`. Requires an `admin` token. The account is kept, not deleted.

    Returns `401` without a valid token, `403` for any other role, `404` if no customer has this ID, and `409` if the customer is already deactivated.
    """
    try:
        return _to_response(service.deactivate_customer(customer_id))
    except CustomerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CustomerAlreadyDeactivatedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except DataAccessError as exc:
        raise _data_error(exc) from exc
