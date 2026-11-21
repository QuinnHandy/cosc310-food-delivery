from decimal import Decimal

from app.core.errors import (
    BusinessRuleError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.repositories.cart_repository import CartRepository
from app.repositories.menu_repository import MenuItemNotFoundError
from app.schemas.cart import (
    MAX_QUANTITY,
    Cart,
    CartLine,
    CartLineResponse,
    CartResponse,
    CartStatus,
)
from app.schemas.menu import MenuItem
from app.schemas.user import User
from app.services.customer_service import CustomerNotAllowedError, CustomerService
from app.services.menu_service import MenuItemUnavailableError, MenuService
from app.services.pricing import price_lines


class DifferentRestaurantError(ConflictError):
    """Raised when adding items from different restaurants."""


class QuantityLimitError(BusinessRuleError):
    """Raised when an item exceeds the maximum quantity."""


class CartItemNotInCartError(NotFoundError):
    """Raised when an item is not in the cart."""


class CartService:
    """Shopping-cart rules (#89-#92). Does no file access of its own.

    Every change is validated first and saved once at the end, so a refused request never
    changes the stored cart. Totals always use the current menu prices (see pricing.py).

    The rules it shares with checkout are not written here (#109): "is this an active
    customer?" is CustomerService.require_active_customer and "can this item be ordered?" is
    MenuService.get_orderable_item, so the cart and checkout can never disagree.
    """

    def __init__(
        self,
        cart_repository: CartRepository,
        menu_service: MenuService,
        customer_service: CustomerService,
        delivery_fee: Decimal,
    ) -> None:
        self._carts = cart_repository
        self._menus = menu_service
        self._customers = customer_service
        self._delivery_fee = delivery_fee

    # ---- reading ----

    def get_cart(self, customer: User) -> CartResponse:
        """Returns the customer's active cart, creating an empty one the first time."""
        return self.to_response(self._active_cart(customer))

    def get_active_cart(self, customer: User) -> Cart:
        """The stored active cart (created if missing), for other services such as checkout."""
        return self._active_cart(customer)

    def find_active_cart(self, customer: User) -> Cart | None:
        """The stored active cart, or None. Unlike get_active_cart this never creates (writes) one,
        so checkout can refuse an empty cart without touching the cart file."""
        customer = self._customers.require_active_customer(customer)
        return self._carts.get_active_for_customer(customer.id)

    # ---- changes ----

    def add_item(self, customer: User, menu_item_id: int, quantity: int) -> CartResponse:
        """Adds `quantity` of an item, or increases it if the item is already in the cart.

        Raises MenuItemNotFoundError, MenuItemUnavailableError, DifferentRestaurantError or
        QuantityLimitError; the cart is unchanged when any of them is raised.
        """
        cart = self._active_cart(customer)
        item = self._menus.get_orderable_item(menu_item_id)
        if cart.restaurant_id is not None and cart.restaurant_id != item.restaurant_id:
            raise DifferentRestaurantError(
                "Your cart can only contain items from one restaurant. "
                "Clear it or remove those items first."
            )

        lines = [line.model_copy() for line in cart.items]
        existing = next((line for line in lines if line.menu_item_id == menu_item_id), None)
        new_quantity = quantity + (existing.quantity if existing else 0)
        if new_quantity > MAX_QUANTITY:
            raise QuantityLimitError(
                f"You can have at most {MAX_QUANTITY} of one item in your cart "
                f"(you already have {existing.quantity if existing else 0})"
            )
        if existing:
            existing.quantity = new_quantity
        else:
            lines.append(CartLine(menu_item_id=menu_item_id, quantity=quantity))

        updated = cart.model_copy(update={"items": lines, "restaurant_id": item.restaurant_id})
        return self.to_response(self._carts.save(updated))

    def set_quantity(self, customer: User, menu_item_id: int, quantity: int) -> CartResponse:
        """Sets the quantity of an item already in the cart. Raises CartItemNotInCartError."""
        cart = self._active_cart(customer)
        self._require_line(cart, menu_item_id)
        lines = [
            CartLine(menu_item_id=line.menu_item_id, quantity=quantity)
            if line.menu_item_id == menu_item_id
            else line
            for line in cart.items
        ]
        return self.to_response(self._carts.save(cart.model_copy(update={"items": lines})))

    def remove_item(self, customer: User, menu_item_id: int) -> CartResponse:
        """Removes one line. An emptied cart forgets its restaurant. Raises CartItemNotInCartError."""
        cart = self._active_cart(customer)
        self._require_line(cart, menu_item_id)
        lines = [line for line in cart.items if line.menu_item_id != menu_item_id]
        restaurant_id = cart.restaurant_id if lines else None
        updated = cart.model_copy(update={"items": lines, "restaurant_id": restaurant_id})
        return self.to_response(self._carts.save(updated))

    def clear(self, customer: User) -> CartResponse:
        """Empties the cart, so items from any restaurant can be added afterwards."""
        cart = self._active_cart(customer)
        updated = cart.model_copy(update={"items": [], "restaurant_id": None})
        return self.to_response(self._carts.save(updated))

    def mark_checked_out(self, cart: Cart) -> Cart:
        """Closes a cart once an order has been made from it (#94).

        The cart keeps its lines as a record. The customer's next `get_cart` finds no active
        cart and creates a new empty one.
        """
        return self._carts.save(cart.model_copy(update={"status": CartStatus.checked_out}))

    # ---- pricing ----

    def to_response(self, cart: Cart) -> CartResponse:
        """Prices a cart with the current menu: names, unit prices, line totals and totals."""
        items: list[MenuItem] = [self._menus.get_item(line.menu_item_id) for line in cart.items]
        breakdown = price_lines(
            [(item.price, line.quantity) for item, line in zip(items, cart.items)],
            self._delivery_fee,
        )
        lines = [
            CartLineResponse(
                menu_item_id=line.menu_item_id,
                name=item.name,
                unit_price=float(priced.unit_price),
                quantity=line.quantity,
                line_total=float(priced.line_total),
                is_available=MenuService.is_orderable(item),
            )
            for item, line, priced in zip(items, cart.items, breakdown.lines)
        ]
        return CartResponse(
            id=cart.id,
            customer_id=cart.customer_id,
            restaurant_id=cart.restaurant_id,
            status=cart.status,
            items=lines,
            subtotal=float(breakdown.subtotal),
            delivery_fee=float(breakdown.delivery_fee),
            total=float(breakdown.total),
        )

    # ---- helpers ----

    def _active_cart(self, customer: User) -> Cart:
        # Checked here as well as by the route's auth dependency, so the rule holds for any
        # caller of the service, not only HTTP requests.
        customer = self._customers.require_active_customer(customer)
        return self._carts.get_active_for_customer(customer.id) or self._carts.add(customer.id)

    @staticmethod
    def _require_line(cart: Cart, menu_item_id: int) -> None:
        if not any(line.menu_item_id == menu_item_id for line in cart.items):
            raise CartItemNotInCartError(f"Menu item {menu_item_id} is not in your cart")


__all__ = [
    "CartService",
    "CartItemNotInCartError",
    "CustomerNotAllowedError",
    "DifferentRestaurantError",
    "MenuItemNotFoundError",
    "MenuItemUnavailableError",
    "QuantityLimitError",
]
