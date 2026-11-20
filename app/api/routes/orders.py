from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from app.api.dependencies import require_role
from app.api.openapi import NOT_ALLOWED, NOT_SIGNED_IN, data_error
from app.api.routes.checkout import get_order_repository
from app.repositories.order_repository import OrderNotFoundError, OrderRepository
from app.repositories.restaurant_repository import DataAccessError
from app.schemas.common import ErrorResponse
from app.schemas.order import Order
from app.schemas.user import User
from app.services.order_service import OrderNotAllowedError, OrderService

router = APIRouter(prefix="/orders", tags=["orders"])

OrderId = Annotated[int, Path(description="ID of the order.")]

# Customers see their own orders; admins see any order. Other roles get 403.
CustomerOrAdmin = Annotated[User, Depends(require_role("customer", "admin"))]


def get_order_service(
    order_repository: OrderRepository = Depends(get_order_repository),
) -> OrderService:
    return OrderService(order_repository)


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
    except OrderNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DataAccessError as exc:
        raise HTTPException(status_code=500, detail="Could not access order data") from exc


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
