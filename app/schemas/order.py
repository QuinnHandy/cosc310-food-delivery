"""Order models (#93).

An order is a record of what was bought, so it stores a *snapshot*: each line keeps the item's
name and the unit price at the moment of checkout, plus the totals the customer was charged.
Editing or deactivating a menu item later never changes an order that already exists.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class OrderStatus(str, Enum):
    """Where the order is. M2 only places orders; later milestones add the delivery steps."""

    placed = "placed"


class OrderLine(BaseModel):
    """One item in an order, as it was at checkout."""

    menu_item_id: int = Field(description="ID of the menu item (kept for reference only).")
    name: str = Field(min_length=1, description="Item name at checkout.")
    unit_price: float = Field(ge=0, description="Price of one item at checkout, in dollars.")
    quantity: int = Field(ge=1, description="How many were ordered.")
    line_total: float = Field(ge=0, description="unit_price x quantity, rounded to cents.")


class OrderDraft(BaseModel):
    """Everything about an order except the ID and time, which the repository assigns.

    Checkout (#94) builds one of these from the cart; it is never sent by a client.
    """

    customer_id: int = Field(description="ID of the customer (user) who placed the order.")
    restaurant_id: int = Field(description="Restaurant every item was ordered from.")
    restaurant_name: str = Field(
        min_length=1, description="Restaurant name at checkout, kept so the order still reads correctly if it is renamed."
    )
    items: list[OrderLine] = Field(min_length=1, description="Lines in the order they were in the cart.")
    subtotal: float = Field(ge=0, description="Sum of the line totals.")
    delivery_fee: float = Field(ge=0, description="Delivery fee charged.")
    total: float = Field(ge=0, description="subtotal + delivery_fee.")
    delivery_address: str = Field(
        default="", description="Customer's delivery address at checkout."
    )


class Order(OrderDraft):
    """An order as stored in data/orders.json."""

    id: int = Field(description="Server-assigned unique ID. Never changes and is never reused.")
    status: OrderStatus = Field(default=OrderStatus.placed, description="Current order status.")
    created_at: datetime = Field(description="When the order was placed (UTC).")
