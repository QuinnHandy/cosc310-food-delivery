from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_checkout_service, require_role
from app.api.openapi import NOT_ALLOWED, NOT_SIGNED_IN, data_error
from app.schemas.common import ErrorResponse
from app.schemas.order import Order
from app.schemas.user import User
from app.services.checkout_service import CheckoutService

router = APIRouter(tags=["checkout"])

CustomerOnly = Annotated[User, Depends(require_role("customer"))]


CHECKOUT_CONFLICT = {
    409: {
        "model": ErrorResponse,
        "description": (
            "The cart is empty, or its restaurant or one of its items no longer exists, is "
            "deactivated or is unavailable (the message names the item). Nothing is saved."
        ),
        "content": {"application/json":
                    {"example": {
                        "detail": "Kung Pao Chicken is not available to order right now",
                        "code": "conflict",
                    }
                }
            }
        },
    }


CHECKOUT_INVALID = {
    422: {
        "model": ErrorResponse,
        "description": (
            "The customer has no delivery address, "
            "or a cart line has an invalid quantity."
        ),
        "content": {
            "application/json": {
                "example": {
                    "detail": "Add a delivery address to your profile before checking out",
                    "code": "business_rule",
                }
            }
        },
    }
}



@router.post(
    "/checkout",
    response_model=Order,
    status_code=201,
    summary="Check out my cart",
    responses={
        **NOT_SIGNED_IN,
        **NOT_ALLOWED,
        **CHECKOUT_CONFLICT,
        **CHECKOUT_INVALID,
        **data_error("Stored order, cart or menu data could not be read or saved."),
    },
)
def checkout(customer: CustomerOnly, service: CheckoutService = Depends(get_checkout_service)) -> Order:
    """Places an order from the signed-in customer's active cart and returns it with `201`.

    There is no request body: the cart, the delivery address and the prices all come from the
    server. Prices are recalculated from the **current** menu, so if a price changed after the
    item was added, the order uses the new price. The order keeps a snapshot of each item's name and
    price, so later menu edits never change it.

    Everything is checked before anything is saved: `403` for another role or a deactivated
    account, `422` for a missing delivery address, `409` for an empty cart or a restaurant or item that no longer exists or is
    unavailable (the message names the item). The order is saved first and the cart is closed
    afterwards, so a failed save leaves the cart unchanged. After checkout, `GET /cart` returns a
    new empty cart.
    """
    return service.checkout(customer)
