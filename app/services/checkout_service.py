"""Checkout rules (#94): turns the customer's active cart into an order.

CheckoutService works only through the existing services and repositories (customers, cart,
menu, restaurants, orders). It never opens their JSON files and never copies their data.

The order of work matters:
1. Check everything first (customer, address, cart, restaurant, every item, quantities).
   Nothing is written if any check fails.
2. Price the cart from the *current* menu with the shared pricing function (pricing.py), never
   from prices the client or the cart supplied.
3. Save the order first, then mark the cart `checked_out`. If saving the order fails, the
   cart is left exactly as it was, so the customer can try again.

Rules shared with the cart are not re-implemented here (#109): the customer check is
CustomerService.require_active_customer and the item check is MenuService.get_orderable_item.
This service only turns their errors into checkout errors, so every reason checkout is
refused is still a CheckoutError.
"""

from decimal import Decimal

from app.core.errors import (
    BusinessRuleError,
    ConflictError,
    ForbiddenError,
)
from app.repositories.menu_repository import MenuItemNotFoundError
from app.repositories.order_repository import OrderRepository
from app.repositories.restaurant_repository import (
    RestaurantNotFoundError,
    RestaurantRepository,
)
from app.schemas.cart import MAX_QUANTITY, Cart
from app.schemas.menu import MenuItem
from app.schemas.order import Order, OrderDraft, OrderLine
from app.schemas.user import User
from app.services.cart_service import CartService
from app.services.customer_service import CustomerNotAllowedError, CustomerService
from app.services.menu_service import MenuItemUnavailableError, MenuService
from app.services.pricing import price_lines


class CheckoutError(ConflictError):
    """Base class for checkout errors (409 by default)."""


class CheckoutNotAllowedError(ForbiddenError, CheckoutError):
    """Customer is not authorized to check out (403)."""


class DeliveryAddressRequiredError(BusinessRuleError, CheckoutError):
    """Customer has no delivery address (422)."""


class EmptyCartError(CheckoutError):
    """Cart is empty (409)."""


class CartChangedError(CheckoutError):
    """A restaurant or item is no longer orderable (409)."""


class InvalidQuantityError(BusinessRuleError, CheckoutError):
    """A cart line has an invalid quantity (422)."""

class CheckoutService:
    """Places an order from the signed-in customer's cart."""

    def __init__(
        self,
        customer_service: CustomerService,
        cart_service: CartService,
        menu_service: MenuService,
        restaurant_repository: RestaurantRepository,
        order_repository: OrderRepository,
        delivery_fee: Decimal,
    ) -> None:
        self._customers = customer_service
        self._carts = cart_service
        self._menus = menu_service
        self._restaurants = restaurant_repository
        self._orders = order_repository
        self._delivery_fee = delivery_fee

    def checkout(self, user: User) -> Order:
        """Creates an order from the user's active cart and returns it.

        Raises a CheckoutError subclass (nothing is written) when any rule fails.
        DataAccessError from a repository passes through, and the cart is then unchanged.
        """
        customer = self._require_active_customer(user)
        delivery_address = customer.delivery_address.strip()
        if not delivery_address:
            raise DeliveryAddressRequiredError(
                "Add a delivery address to your profile before checking out"
            )

        cart = self._carts.find_active_cart(customer)  # never creates a cart (no writes yet)
        if cart is None or not cart.items or cart.restaurant_id is None:
            raise EmptyCartError("Your cart is empty")

        try:
            restaurant = self._restaurants.get(cart.restaurant_id)
        except RestaurantNotFoundError as exc:
            raise CartChangedError(
                "The restaurant in your cart no longer exists. Clear your cart and start again."
            ) from exc

        items = self._current_items(cart)
        draft = self._build_draft(customer, delivery_address, restaurant.id, restaurant.name, cart, items)

        order = self._orders.add(draft)  # if this raises, the cart has not been touched
        self._carts.mark_checked_out(cart)
        return order

    # ---- steps ----

    def _require_active_customer(self, user: User) -> User:
        """The shared customer rule, reported as a checkout error."""
        try:
            return self._customers.require_active_customer(user)
        except CustomerNotAllowedError as exc:
            raise CheckoutNotAllowedError(str(exc)) from exc

    def _current_items(self, cart: Cart) -> list[MenuItem]:
        """The current menu item for every cart line, checking each is still orderable."""
        items = []
        for line in cart.items:
            if not 1 <= line.quantity <= MAX_QUANTITY:
                raise InvalidQuantityError(
                    f"Quantity for menu item {line.menu_item_id} must be 1 to {MAX_QUANTITY}"
                )
            try:
                item = self._menus.get_orderable_item(line.menu_item_id)
            except MenuItemNotFoundError as exc:
                raise CartChangedError(
                    f"Menu item {line.menu_item_id} no longer exists. Remove it from your cart."
                ) from exc
            except MenuItemUnavailableError as exc:
                raise CartChangedError(str(exc)) from exc
            if item.restaurant_id != cart.restaurant_id:
                raise CartChangedError(f"{item.name} no longer belongs to this restaurant")
            items.append(item)
        return items

    def _build_draft(
        self,
        customer: User,
        delivery_address: str,
        restaurant_id: int,
        restaurant_name: str,
        cart: Cart,
        items: list[MenuItem],
    ) -> OrderDraft:
        breakdown = price_lines(
            [(item.price, line.quantity) for item, line in zip(items, cart.items)],
            self._delivery_fee,
        )
        lines = [
            OrderLine(
                menu_item_id=item.id,
                name=item.name,
                unit_price=float(priced.unit_price),
                quantity=line.quantity,
                line_total=float(priced.line_total),
            )
            for item, line, priced in zip(items, cart.items, breakdown.lines)
        ]
        return OrderDraft(
            customer_id=customer.id,
            restaurant_id=restaurant_id,
            restaurant_name=restaurant_name,
            items=lines,
            subtotal=float(breakdown.subtotal),
            delivery_fee=float(breakdown.delivery_fee),
            total=float(breakdown.total),
            delivery_address=delivery_address,
        )
