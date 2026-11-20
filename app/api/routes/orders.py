from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from app.api.dependencies import get_customer_service, require_role
from app.api.openapi import NOT_ALLOWED, NOT_SIGNED_IN, data_error
from app.api.routes.checkout import get_order_repository
from app.repositories.order_repository import OrderRepository
from app.repositories.restaurant_repository import DataAccessError
from app.schemas.common import ErrorResponse
from app.schemas.order import Order
from app.schemas.user import User
from app.services.customer_service import CustomerNotFoundError, CustomerService
from app.services.order_service import OrderService

router = APIRouter(tags=["orders"])

CustomerId = Annotated[int, Path(description="ID of the customer.")]

CUSTOMER_NOT_FOUND = {
    404: {
        "model": ErrorResponse,
        "description": "No customer has this ID (owner and admin IDs count as not found).",
        "content": {"application/json": {"example": {"detail": "Customer 99 not found"}}},
    }
}
DATA_ERROR = data_error("Stored order or user data could not be read.")


def get_order_service(
    order_repository: OrderRepository = Depends(get_order_repository),
    customer_service: CustomerService = Depends(get_customer_service),
) -> OrderService:
    return OrderService(order_repository, customer_service)


def _data_error(exc: DataAccessError) -> HTTPException:
    # Fixed message: DataAccessError text can quote stored records.
    return HTTPException(status_code=500, detail="Could not access order data")


# "/customers/me/orders" must stay above "/customers/{customer_id}/orders", or "me" would be
# read as a customer ID and answered with 422.
@router.get(
    "/customers/me/orders",
    response_model=list[Order],
    summary="List my orders",
    responses={**NOT_SIGNED_IN, **NOT_ALLOWED, **DATA_ERROR},
)
def list_my_orders(
    user: User = Depends(require_role("customer")),
    service: OrderService = Depends(get_order_service),
) -> list[Order]:
    """Returns the signed-in customer's orders, newest first. Requires a `customer` token.

    Only the caller's own orders are returned. A customer with no orders gets `200` with an empty list `[]`, not a `404`. Each order keeps the item names and prices from checkout.

    Returns `401` without a valid token and `403` for other roles or a deactivated account.
    """
    try:
        return service.list_my_orders(user)
    except DataAccessError as exc:
        raise _data_error(exc) from exc


@router.get(
    "/customers/{customer_id}/orders",
    response_model=list[Order],
    summary="List a customer's orders (admin)",
    dependencies=[Depends(require_role("admin"))],
    responses={**NOT_SIGNED_IN, **NOT_ALLOWED, **CUSTOMER_NOT_FOUND, **DATA_ERROR},
)
def list_customer_orders(
    customer_id: CustomerId,
    service: OrderService = Depends(get_order_service),
) -> list[Order]:
    """Returns any customer's orders, newest first. Requires an `admin` token.

    An existing customer with no orders gets `200` with an empty list `[]`.

    Returns `401` without a valid token, `403` for any other role, `404` if no customer has this ID, and `422` if the ID is not an integer.
    """
    try:
        return service.list_orders_for_customer(customer_id)
    except CustomerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DataAccessError as exc:
        raise _data_error(exc) from exc
