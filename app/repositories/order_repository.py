from datetime import datetime, timezone
from pathlib import Path

from app.repositories.json_store import JsonStore, next_id
from app.schemas.order import Order, OrderDraft


class OrderNotFoundError(Exception):
    """Raised when an order ID does not exist."""


class OrderRepository:
    """Reads and writes orders in a JSON file. A missing file means there are no orders yet.

    Only stores orders; the rules about who may place or see one live in the service.
    Orders are never edited or deleted here, so there is no update method.
    """

    def __init__(self, order_file: Path) -> None:
        self._store = JsonStore(order_file, Order, "order", missing_ok=True)

    def list_all(self) -> list[Order]:
        orders = self._store.load()
        self._store.require_unique_ids(orders)
        return orders

    def get_by_id(self, order_id: int) -> Order:
        for order in self.list_all():
            if order.id == order_id:
                return order
        raise OrderNotFoundError(f"Order {order_id} not found")

    def list_for_customer(self, customer_id: int) -> list[Order]:
        """The customer's orders, newest first. Empty if they have none."""
        mine = [order for order in self.list_all() if order.customer_id == customer_id]
        return sorted(mine, key=lambda order: order.id, reverse=True)

    def add(self, draft: OrderDraft) -> Order:
        """Saves a new order with the next unused ID and the current time, and returns it."""
        orders = self.list_all()
        order = Order(
            **draft.model_dump(),
            id=next_id(orders),
            created_at=datetime.now(timezone.utc),
        )
        self._store.save([*orders, order])
        return order
