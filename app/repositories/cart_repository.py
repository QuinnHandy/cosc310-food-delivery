from pathlib import Path

from app.repositories.json_store import DataAccessError, JsonStore, next_id
from app.schemas.cart import Cart, CartStatus


class CartNotFoundError(Exception):
    """Raised when a cart ID does not exist."""


class CartRepository:
    """Reads and writes carts in a JSON file. A missing file means there are no carts yet.

    Only stores carts; the rules about what may go in one live in CartService.
    """

    def __init__(self, cart_file: Path) -> None:
        self._store = JsonStore(cart_file, Cart, "cart", missing_ok=True)

    def list_all(self) -> list[Cart]:
        carts = self._store.load()
        self._store.require_unique_ids(carts)
        active_owners = [c.customer_id for c in carts if c.status == CartStatus.active]
        if len(active_owners) != len(set(active_owners)):
            raise DataAccessError(
                f"Cart data file has more than one active cart for a customer: {self._store.path}"
            )
        return carts

    def _save(self, carts: list[Cart]) -> None:
        self._store.save(carts)

    def get_by_id(self, cart_id: int) -> Cart:
        for cart in self.list_all():
            if cart.id == cart_id:
                return cart
        raise CartNotFoundError(f"Cart {cart_id} not found")

    def get_active_for_customer(self, customer_id: int) -> Cart | None:
        """Returns the customer's active cart, or None. Checked-out carts are ignored."""
        for cart in self.list_all():
            if cart.customer_id == customer_id and cart.status == CartStatus.active:
                return cart
        return None

    def add(self, customer_id: int) -> Cart:
        """Creates and saves an empty active cart with the next unused ID."""
        carts = self.list_all()
        if any(c.customer_id == customer_id and c.status == CartStatus.active for c in carts):
            raise DataAccessError(f"Customer {customer_id} already has an active cart")
        cart = Cart(id=next_id(carts), customer_id=customer_id)
        self._save([*carts, cart])
        return cart

    def save(self, cart: Cart) -> Cart:
        """Replaces the stored cart that has the same ID. Raises CartNotFoundError if there is none."""
        carts = self.list_all()
        for index, existing in enumerate(carts):
            if existing.id == cart.id:
                carts[index] = Cart.model_validate(cart.model_dump())
                self._save(carts)
                return carts[index]
        raise CartNotFoundError(f"Cart {cart.id} not found")
