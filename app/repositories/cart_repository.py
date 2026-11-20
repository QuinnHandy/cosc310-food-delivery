import json
from pathlib import Path

from pydantic import ValidationError

from app.repositories.restaurant_repository import DataAccessError, write_json_atomic
from app.schemas.cart import Cart, CartStatus


class CartNotFoundError(Exception):
    """Raised when a cart ID does not exist."""


class CartRepository:
    """Reads and writes carts in a JSON file. A missing file means there are no carts yet.

    Only stores carts; the rules about what may go in one live in CartService.
    """

    def __init__(self, cart_file: Path) -> None:
        self._cart_file = Path(cart_file)

    def list_all(self) -> list[Cart]:
        try:
            raw = self._cart_file.read_text(encoding="utf-8")
        except FileNotFoundError:
            return []
        except OSError as exc:
            raise DataAccessError(f"Could not read cart data file: {self._cart_file}") from exc

        try:
            records = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise DataAccessError(f"Cart data file is not valid JSON: {self._cart_file}") from exc

        if not isinstance(records, list):
            raise DataAccessError(f"Cart data file must contain a JSON list: {self._cart_file}")

        try:
            carts = [Cart.model_validate(record) for record in records]
        except ValidationError as exc:
            raise DataAccessError(f"Cart record does not match the Cart model: {exc}") from exc

        ids = [c.id for c in carts]
        if len(ids) != len(set(ids)):
            raise DataAccessError(f"Cart data file contains duplicate cart IDs: {self._cart_file}")
        active_owners = [c.customer_id for c in carts if c.status == CartStatus.active]
        if len(active_owners) != len(set(active_owners)):
            raise DataAccessError(
                f"Cart data file has more than one active cart for a customer: {self._cart_file}"
            )
        return carts

    def _save(self, carts: list[Cart]) -> None:
        write_json_atomic(self._cart_file, [c.model_dump(mode="json") for c in carts])

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
        cart = Cart(id=max((c.id for c in carts), default=0) + 1, customer_id=customer_id)
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
