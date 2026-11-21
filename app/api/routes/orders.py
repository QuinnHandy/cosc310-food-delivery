from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.api.dependencies import get_order_service, require_role
from app.api.openapi import NOT_ALLOWED, NOT_SIGNED_IN, data_error
from app.schemas.common import ErrorResponse
from app.schemas.order import Order
from app.schemas.user import User
from app.services.order_service import OrderService

router = APIRouter(tags=["orders"])

CustomerId = Annotated[int, Path(description="ID of the customer.")]
OrderId = Annotated[int, Path(description="ID of the order.")]

CUSTOMER_NOT_FOUND = {
    404: {
        "model": ErrorResponse,
        "description": "No customer has this ID (owner and admin IDs count as not found).",
        "content": {"application/json": {"example": {"detail": "Customer 99 not found", "code": "not_found",}}},
    }
}
ORDER_NOT_FOUND = {
    404: {
        "model": ErrorResponse,
        "description": "No order has this ID.",
        "content": {"application/json": {"example": {"detail": "Order 99 not found", "code": "not_found",}}},
    }
}

ORDER_NOT_YOURS = {
    403: {
        "model": ErrorResponse,
        "description": (
            "The account is deactivated, the role is not allowed "
            "(restaurant owners), or the order belongs to another customer."
        ),
        "content": {
            "application/json": {
                "example": {
                    "detail": "You do not have permission to view this order",
                    "code": "forbidden",
                }
            }
        },
    }
}

DATA_ERROR = data_error("Stored order or user data could not be read.")


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
    return service.list_my_orders(user)


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
    return service.list_orders_for_customer(customer_id)


@router.get(
    "/orders/{order_id}",
    response_model=Order,
    summary="View one order",
    responses={**NOT_SIGNED_IN, **ORDER_NOT_YOURS, **ORDER_NOT_FOUND, **DATA_ERROR},
)
def get_order(
    order_id: OrderId,
    user: User = Depends(require_role("customer", "admin")),
    service: OrderService = Depends(get_order_service),
) -> Order:
    """Returns one order with the item names, prices and totals saved at checkout. A `customer` token sees only their own orders; an `admin` token sees any order.

    Returns `401` without a valid token, `403` for a restaurant owner, a deactivated account, or a customer asking for another customer's order, `404` if no order has this ID, and `422` if the ID is not an integer.
    """
    return service.get_order(user, order_id)
