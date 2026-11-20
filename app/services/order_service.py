"""Order viewing rules (#95, #96). Does no file access of its own.

Orders are a record of what was bought and what was paid, so this service only reads them:
the order, its item snapshot and its totals are returned exactly as they were saved at
checkout, whatever has happened to the menu since.
"""

from app.repositories.order_repository import OrderNotFoundError, OrderRepository
from app.schemas.order import Order
from app.schemas.user import User, UserRole
from app.services.customer_service import CustomerNotFoundError, CustomerService


class OrderNotAllowedError(Exception):
    """Raised when the user may not see this order (someone else's, or a role with no orders)."""


class OrderService:
    """Who may see which order. A customer sees their own orders; an admin sees any order."""

    def __init__(self, order_repository: OrderRepository, customer_service: CustomerService) -> None:
        self._orders = order_repository
        self._customers = customer_service

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


    def list_my_orders(self, user: User) -> list[Order]:
        """The signed-in customer's own orders, newest first. An empty list if they have none.

        Raises OrderNotAllowedError for a deactivated account or any role other than customer.
        """
        if not user.is_active:
            raise OrderNotAllowedError("This account has been deactivated")
        if user.role != UserRole.customer:
            raise OrderNotAllowedError("Only customers have orders of their own")
        return self._orders.list_for_customer(user.id)

    def list_orders_for_customer(self, user: User, customer_id: int) -> list[Order]:
        """Any customer's orders, newest first (admin only). An empty list if they have none.

        Raises OrderNotAllowedError if the caller is not an active admin, and
        CustomerNotFoundError if no customer has this ID (owner and admin IDs count as not found).
        """
        if not user.is_active or user.role != UserRole.admin:
            raise OrderNotAllowedError("Only admins can view another customer's orders")
        self._customers.get_customer(customer_id)  # raises CustomerNotFoundError
        return self._orders.list_for_customer(customer_id)


__all__ = ["OrderService", "OrderNotAllowedError", "OrderNotFoundError", "CustomerNotFoundError"]
