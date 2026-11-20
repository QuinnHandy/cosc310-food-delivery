"""Order viewing rules (#95). Does no file access of its own.

Orders are a record of what was bought and what was paid, so this service only reads them:
the order, its item snapshot and its totals are returned exactly as they were saved at
checkout, whatever has happened to the menu since.
"""

from app.repositories.order_repository import OrderNotFoundError, OrderRepository
from app.schemas.order import Order
from app.schemas.user import User, UserRole


class OrderNotAllowedError(Exception):
    """Raised when the user may not see this order (someone else's, or a role with no orders)."""


class OrderService:
    """Who may see which order. A customer sees their own orders; an admin sees any order."""

    def __init__(self, order_repository: OrderRepository) -> None:
        self._orders = order_repository

    def get_order(self, user: User, order_id: int) -> Order:
        """Returns one order.

        Raises OrderNotFoundError for an unknown ID and OrderNotAllowedError when a customer asks
        for another customer's order, or the user is deactivated or has a role with no orders.
        """
        if not user.is_active:
            raise OrderNotAllowedError("This account has been deactivated")
        if user.role not in (UserRole.customer, UserRole.admin):
            raise OrderNotAllowedError("Only customers and admins can view orders")

        order = self._orders.get_by_id(order_id)  # raises OrderNotFoundError
        if user.role == UserRole.customer and order.customer_id != user.id:
            raise OrderNotAllowedError("You can only view your own orders")
        return order


__all__ = ["OrderService", "OrderNotAllowedError", "OrderNotFoundError"]
