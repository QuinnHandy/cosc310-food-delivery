from typing import Annotated

from fastapi import APIRouter, Depends, Path

from app.api.dependencies import get_cart_service, require_role
from app.api.openapi import NOT_ALLOWED, NOT_SIGNED_IN, data_error
from app.schemas.cart import CartItemAdd, CartItemUpdate, CartResponse
from app.schemas.common import ErrorResponse
from app.schemas.user import User
from app.services.cart_service import CartService

router = APIRouter(prefix="/cart", tags=["cart"])

MenuItemId = Annotated[int, Path(description="ID of a menu item that is in the cart.")]

# Every cart endpoint is for signed-in, active customers only.
CustomerOnly = Annotated[User, Depends(require_role("customer"))]



def _error(status: int, description: str, example: str) -> dict:
    codes = {
        404: "not_found",
        409: "conflict",
        422: "business_rule",
    }

    return {
        status: {
            "model": ErrorResponse,
            "description": description,
            "content": {
                "application/json": {
                    "example": {
                        "detail": example,
                        "code": codes[status],
                    }
                }
            },
        }
    }



ITEM_NOT_FOUND = _error(404, "No menu item has this ID.", "Menu item 99 not found")
NOT_IN_CART = _error(404, "This menu item is not in the cart.", "Menu item 3 is not in your cart")
ADD_CONFLICT = _error(
    409,
    "The item is unavailable or deactivated, or comes from a different restaurant than the items already in the cart.",
    "Your cart can only contain items from one restaurant. Clear it or remove those items first.",
)
COMMON = {
    **NOT_SIGNED_IN,
    **NOT_ALLOWED,
    **data_error("Stored cart or menu data could not be read or saved."),
}


@router.get("", response_model=CartResponse, summary="Get my cart", responses=COMMON)
def get_cart(customer: CustomerOnly, service: CartService = Depends(get_cart_service)) -> CartResponse:
    """Returns the signed-in customer's active cart, creating an empty one the first time. A customer only ever has one active cart, so repeated calls return the same `id`.

    Each line shows the item's **current** name and price; `subtotal`, `delivery_fee` and `total` are calculated by the backend (the fee is 0 for an empty cart). Returns `401` without a valid token and `403` for other roles or a deactivated account.
    """
    return service.get_cart(customer)


@router.post(
    "/items",
    response_model=CartResponse,
    summary="Add an item to my cart",
    responses={**COMMON, **ITEM_NOT_FOUND, **ADD_CONFLICT},
)
def add_item(
    body: CartItemAdd,
    customer: CustomerOnly,
    service: CartService = Depends(get_cart_service),
) -> CartResponse:
    """Adds `quantity` (default 1) of a menu item and returns the updated cart. If the item is already in the cart, its quantity goes up.

    An empty cart takes on the restaurant of its first item; after that, items from another restaurant are refused with `409`. Returns `404` for an unknown item, `409` for an unavailable or deactivated item, and `422` if `quantity` is not a whole number from 1 to 20 (field error list) or the line would go above 20 (`{"detail": "You can have at most 20 of one item in your cart (you already have 18)"}`). A refused request leaves the cart unchanged. There is no price field: prices always come from the menu.
    """
    return service.add_item(customer, body.menu_item_id, body.quantity)


@router.patch(
    "/items/{menu_item_id}",
    response_model=CartResponse,
    summary="Change the quantity of an item in my cart",
    responses={**COMMON, **NOT_IN_CART},
)
def set_quantity(
    menu_item_id: MenuItemId,
    body: CartItemUpdate,
    customer: CustomerOnly,
    service: CartService = Depends(get_cart_service),
) -> CartResponse:
    """Sets the quantity of an item already in the cart and returns the updated cart.

    Returns `404` if the item is not in the cart and `422` if `quantity` is not a whole number from 1 to 20.
    """
    return service.set_quantity(customer, menu_item_id, body.quantity)


@router.delete(
    "/items/{menu_item_id}",
    response_model=CartResponse,
    summary="Remove an item from my cart",
    responses={**COMMON, **NOT_IN_CART},
)
def remove_item(
    menu_item_id: MenuItemId,
    customer: CustomerOnly,
    service: CartService = Depends(get_cart_service),
) -> CartResponse:
    """Removes one line and returns the updated cart. Removing the last line frees the cart for any restaurant.

    Returns `404` if the item is not in the cart.
    """
    return service.remove_item(customer, menu_item_id)


@router.delete("/items", response_model=CartResponse, summary="Clear my cart", responses=COMMON)
def clear_cart(customer: CustomerOnly, service: CartService = Depends(get_cart_service)) -> CartResponse:
    """Removes every item and returns the empty cart (same `id`). Its restaurant is reset, so items from any restaurant can be added afterwards."""
    return service.clear(customer)
