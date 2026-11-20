"""Shopping cart models (#88-#92).

A stored cart holds only menu item IDs and quantities. Prices are never stored or accepted
from the client: the service reads the current menu price whenever a cart is shown, and
checkout recalculates them again.
"""

from enum import Enum

from pydantic import BaseModel, Field

MAX_QUANTITY = 20


class CartStatus(str, Enum):
    """`active` while the customer is shopping; `checked_out` once an order has been made from it."""

    active = "active"
    checked_out = "checked_out"


class CartLine(BaseModel):
    """One menu item in a stored cart."""

    menu_item_id: int = Field(description="ID of the menu item.")
    quantity: int = Field(ge=1, le=MAX_QUANTITY, description=f"How many, 1 to {MAX_QUANTITY}.")


class Cart(BaseModel):
    """A cart as stored in data/carts.json."""

    id: int = Field(description="Server-assigned unique ID. Never changes and is never reused.")
    customer_id: int = Field(description="ID of the customer (user) who owns the cart.")
    restaurant_id: int | None = Field(
        default=None,
        description="Restaurant every item comes from. Null while the cart is empty.",
    )
    status: CartStatus = Field(default=CartStatus.active, description="'active' or 'checked_out'.")
    items: list[CartLine] = Field(default_factory=list, description="Lines in the order they were added.")


# ---- Requests. Strict ints: "2", 2.5 and true are rejected with 422, not converted. ----

class CartItemAdd(BaseModel):
    """Request body for adding a menu item to the cart. There is no price field on purpose."""

    menu_item_id: int = Field(strict=True, description="ID of the menu item to add.")
    quantity: int = Field(
        default=1,
        strict=True,
        ge=1,
        le=MAX_QUANTITY,
        description=f"How many to add, 1 to {MAX_QUANTITY}. Added to any quantity already in the cart.",
    )


class CartItemUpdate(BaseModel):
    """Request body for setting the quantity of an item already in the cart."""

    quantity: int = Field(
        strict=True, ge=1, le=MAX_QUANTITY, description=f"New quantity, 1 to {MAX_QUANTITY}."
    )


# ---- Responses. Every money value is calculated by the backend from current menu prices. ----

class CartLineResponse(BaseModel):
    """One cart line with its current price."""

    menu_item_id: int = Field(description="ID of the menu item.")
    name: str = Field(description="Current name of the menu item.")
    unit_price: float = Field(description="Current menu price, in dollars.")
    quantity: int = Field(description="How many.")
    line_total: float = Field(description="unit_price x quantity, rounded to cents.")
    is_available: bool = Field(
        description="False if the item has since become unavailable or been deactivated; checkout will refuse it."
    )


class CartResponse(BaseModel):
    """The customer's cart with backend-calculated totals."""

    id: int = Field(description="Cart ID. Stays the same until the cart is checked out.")
    customer_id: int = Field(description="ID of the customer who owns the cart.")
    restaurant_id: int | None = Field(description="Restaurant of the items. Null while empty.")
    status: CartStatus = Field(description="'active' or 'checked_out'.")
    items: list[CartLineResponse] = Field(description="Lines in the order they were added.")
    subtotal: float = Field(description="Sum of the line totals.")
    delivery_fee: float = Field(description="Flat delivery fee; 0 for an empty cart.")
    total: float = Field(description="subtotal + delivery_fee.")
