"""Order rules (#95, #96): who may see which orders. Does no file access of its own."""

from app.core.errors import ForbiddenError
from app.repositories.order_repository import OrderNotFoundError, OrderRepository
from app.schemas.order import Order
from app.schemas.user import User, UserRole
from app.services.customer_service import CustomerService


class OrderNotAllowedError(ForbiddenError):
    """Raised when a customer asks for an order that belongs to someone else."""


class OrderService:
    """Lists a customer's orders through the order repository.

    A customer only ever sees their own orders: the ID always comes from the signed-in user,
    never from the request. An admin names the customer, and the customer must exist.
    Viewing one order (#95): a customer may only open their own order; an admin may open any.
    """

    def __init__(self, order_repository: OrderRepository, customer_service: CustomerService) -> None:
        self._orders = order_repository
        self._customers = customer_service

    def list_my_orders(self, user: User) -> list[Order]:
        """The signed-in customer's orders, newest first. An empty list if they have none."""
        return self._orders.list_for_customer(user.id)

    def list_orders_for_customer(self, customer_id: int) -> list[Order]:
        """Any customer's orders, newest first (for admins).

        Raises CustomerNotFoundError if the ID is unknown or belongs to an owner or admin.
        An existing customer with no orders gives an empty list.
        """
        self._customers.get_customer(customer_id)
        return self._orders.list_for_customer(customer_id)

    def get_order(self, user: User, order_id: int) -> Order:
        """One order (#95). A customer may view their own; an admin may view any.

        Raises OrderNotFoundError if no order has this ID, and OrderNotAllowedError if a
        customer asks for another customer's order.
        """
        order = self._orders.get_by_id(order_id)
        if user.role != UserRole.admin and order.customer_id != user.id:
            raise OrderNotAllowedError("You do not have permission to view this order")
        return order
