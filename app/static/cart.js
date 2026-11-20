// Cart panel on the customer page (#98). Loaded after api.js and before app.js.
//
// Every number shown here comes from the API's cart response: the page never adds up prices
// or decides what may go in the cart. If the API refuses something (another restaurant, an
// unavailable item, a bad quantity, a deactivated account), its message is shown as-is.

const cartStatusEl = document.getElementById("cart-status");
const cartListEl = document.getElementById("cart-list");
const cartTotalsEl = document.getElementById("cart-totals");
const cartClearButton = document.getElementById("cart-clear");

function money(amount) {
  return `$${Number(amount).toFixed(2)}`; // display only
}

function isSignedInCustomer() {
  const session = Auth.session();
  return Boolean(Auth.token() && session && session.role === "customer");
}

const CartPanel = {
  cart: null,
  // Other parts of the page (checkout, #99) can listen for cart changes.
  listeners: [],

  onChange(listener) {
    this.listeners.push(listener);
  },

  showMessage(text) {
    cartStatusEl.textContent = text;
  },

  render(cart) {
    this.cart = cart;
    cartListEl.replaceChildren();
    const hasItems = Boolean(cart && cart.items.length);
    cartTotalsEl.hidden = !cart;
    cartClearButton.hidden = !hasItems;

    if (cart) {
      for (const line of cart.items) cartListEl.appendChild(this.lineElement(line));
      document.getElementById("cart-subtotal").textContent = money(cart.subtotal);
      document.getElementById("cart-delivery-fee").textContent = money(cart.delivery_fee);
      document.getElementById("cart-total").textContent = money(cart.total);
      if (!hasItems) this.showMessage("Your cart is empty.");
    }
    for (const listener of this.listeners) listener(cart);
  },

  lineElement(line) {
    const item = document.createElement("li");
    item.className = line.is_available ? "cart-line" : "cart-line unavailable";
    item.append(`${line.name} - ${money(line.unit_price)} x `);

    const quantity = document.createElement("input");
    quantity.type = "number";
    quantity.min = "1";
    quantity.max = "20";
    quantity.value = String(line.quantity);
    quantity.setAttribute("aria-label", `Quantity of ${line.name}`);
    quantity.addEventListener("change", () =>
      this.run(() => API.setCartQuantity(line.menu_item_id, Number(quantity.value)), "Quantity updated.")
    );

    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "Remove";
    remove.addEventListener("click", () =>
      this.run(() => API.removeFromCart(line.menu_item_id), `Removed ${line.name}.`)
    );

    item.append(quantity, ` = ${money(line.line_total)} `, remove);
    if (!line.is_available) item.append(" (no longer available - remove it to check out)");
    return item;
  },

  // Runs one cart request, then shows the cart the API returned, or the API's error message.
  // After an error the cart is reloaded, so the page matches what is really stored.
  async run(request, successMessage) {
    try {
      const cart = await request();
      this.render(cart);
      if (cart.items.length) this.showMessage(successMessage);
    } catch (error) {
      if (error.status === 401) return; // api.js is already sending the user to sign in
      this.showMessage(error.message);
      await this.load({ keepMessage: true });
    }
  },

  async load({ keepMessage = false } = {}) {
    if (!isSignedInCustomer()) {
      this.render(null);
      this.showMessage("Sign in as a customer to start a cart.");
      return;
    }
    try {
      const cart = await API.getCart();
      if (!keepMessage) this.showMessage("");
      this.render(cart);
    } catch (error) {
      if (error.status === 401) return;
      this.render(null);
      if (!keepMessage) this.showMessage(error.message);
    }
  },

  add(menuItem) {
    if (!Auth.token()) {
      Auth.goToSignIn("Sign in to add items to your cart.");
      return Promise.resolve();
    }
    return this.run(() => API.addToCart(menuItem.id, 1), `Added ${menuItem.name} to your cart.`);
  },
};

cartClearButton.addEventListener("click", () =>
  CartPanel.run(() => API.clearCart(), "Cart cleared.")
);

CartPanel.load();
