from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from app.api.dependencies import get_order_service, require_role
from app.api.openapi import NOT_ALLOWED, NOT_SIGNED_IN, data_error
from app.repositories.order_repository import OrderNotFoundError
from app.repositories.restaurant_repository import DataAccessError
from app.schemas.common import ErrorResponse
from app.schemas.order import Order
from app.schemas.user import User
from app.services.customer_service import CustomerNotFoundError
from app.services.order_service import OrderNotAllowedError, OrderService

router = APIRouter(prefix="/orders", tags=["orders"])
# The order lists live under /customers/... but belong with the other order endpoints.
customer_orders_router = APIRouter(tags=["orders"])

OrderId = Annotated[int, Path(description="ID of the order.")]

# Customers see their own orders; admins see any order. Other roles get 403.
CustomerOrAdmin = Annotated[User, Depends(require_role("customer", "admin"))]


CustomerId = Annotated[int, Path(description="ID of the customer.")]

# Only customers have orders of their own to list; only admins can list someone else's.
CustomerOnly = Annotated[User, Depends(require_role("customer"))]
AdminOnly = Annotated[User, Depends(require_role("admin"))]


ORDER_NOT_FOUND = {
    404: {
        "model": ErrorResponse,
        "description": "No order has this ID.",
        "content": {"application/json": {"example": {"detail": "Order 99 not found"}}},
    }
}


def _call(action):
    """Runs an OrderService call and turns its errors into HTTP responses."""
    try:
        return action()
    except OrderNotAllowedError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (OrderNotFoundError, CustomerNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DataAccessError as exc:
        raise HTTPException(status_code=500, detail="Could not access order data") from exc


CUSTOMER_NOT_FOUND = {
    404: {
        "model": ErrorResponse,
        "description": "No customer has this ID (owner and admin IDs count as not found).",
        "content": {"application/json": {"example": {"detail": "Customer 99 not found"}}},
    }
}


@router.get(
    "/{order_id}",
    response_model=Order,
    summary="Get one order",
    responses={
        **NOT_SIGNED_IN,
        **NOT_ALLOWED,
        **ORDER_NOT_FOUND,
        **data_error("Stored order data could not be read."),
    },
)
def get_order(
    order_id: OrderId,
    user: CustomerOrAdmin,
    service: OrderService = Depends(get_order_service),
) -> Order:
    """Returns one order with its item snapshot and totals, exactly as they were at checkout.

    Each line keeps the item's name and unit price from the moment of checkout, so changing a menu item's price or name afterwards never changes an order. A customer can only see their own orders; an `admin` can see any order.

    Returns `401` without a valid token, `403` for another customer's order, a deactivated account or a role that has no orders (such as a restaurant owner), and `404` for an unknown order ID.
    """
    return _call(lambda: service.get_order(user, order_id))


@customer_orders_router.get(
    "/customers/me/orders",
    response_model=list[Order],
    summary="List my orders",
    responses={
        **NOT_SIGNED_IN,
        **NOT_ALLOWED,
        **data_error("Stored order data could not be read."),
    },
)
def list_my_orders(
    customer: CustomerOnly, service: OrderService = Depends(get_order_service)
) -> list[Order]:
    """Returns the signed-in customer's own orders, newest first, each with its item snapshot and totals. A customer with no orders gets `200` and an empty list `[]`, not `404`. Other customers' orders are never included.

    Returns `401` without a valid token and `403` for other roles or a deactivated account.
    """
    return _call(lambda: service.list_my_orders(customer))


@customer_orders_router.get(
    "/customers/{customer_id}/orders",
    response_model=list[Order],
    summary="List a customer's orders (admin)",
    responses={
        **NOT_SIGNED_IN,
        **NOT_ALLOWED,
        **CUSTOMER_NOT_FOUND,
        **data_error("Stored order or user data could not be read."),
    },
)
def list_customer_orders(
    customer_id: CustomerId,
    admin: AdminOnly,
    service: OrderService = Depends(get_order_service),
) -> list[Order]:
    """Returns any customer's orders, newest first. Requires an `admin` token. A customer with no orders gets `200` and an empty list `[]`.

    Returns `401` without a valid token, `403` for any other role, `404` if no customer has this ID (owner and admin IDs count as not found), and `422` if the ID is not an integer.
    """
    return _call(lambda: service.list_orders_for_customer(admin, customer_id))
