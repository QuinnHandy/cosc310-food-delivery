"""Order history rules (#96): who may see which orders. Does no file access of its own."""

from app.repositories.order_repository import OrderRepository
from app.schemas.order import Order
from app.schemas.user import User
from app.services.customer_service import CustomerService


class OrderService:
    """Lists a customer's orders through the order repository.

    A customer only ever sees their own orders: the ID always comes from the signed-in user,
    never from the request. An admin names the customer, and the customer must exist.
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
