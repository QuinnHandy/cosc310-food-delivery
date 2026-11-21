// Checkout on the customer page (#99). Loaded after cart.js and order-view.js.
//
// The backend does all the checking (active account, delivery address, items still
// available, current prices) and calculates the order's totals. This only sends the request,
// then shows the order it returns, or the API's message if checkout is refused.

const checkoutButton = document.getElementById("cart-checkout");
const checkoutStatusEl = document.getElementById("checkout-status");
const confirmationEl = document.getElementById("order-confirmation");
const confirmationBodyEl = document.getElementById("order-confirmation-body");

// Show the button only when there is something to check out.
CartPanel.onChange((cart) => {
  checkoutButton.hidden = !(cart && cart.items.length);
});

function showCheckoutError(error) {
  checkoutStatusEl.replaceChildren(error.message);
  // A missing delivery address is fixed on the account page.
  if (error.status === 422 && /address/i.test(error.message)) {
    const link = document.createElement("a");
    link.href = "/account";
    link.textContent = "Add a delivery address";
    checkoutStatusEl.append(" ", link);
  }
}

checkoutButton.addEventListener("click", async () => {
  checkoutButton.disabled = true;
  checkoutStatusEl.textContent = "Placing your order...";
  try {
    const order = await API.checkout();
    checkoutStatusEl.textContent = "";
    confirmationBodyEl.replaceChildren(orderDetailsElement(order));
    confirmationEl.hidden = false;
    await CartPanel.load(); // the backend has closed this cart; the next one starts empty
  } catch (error) {
    if (error.status === 401) return; // api.js is already sending the user to sign in
    showCheckoutError(error);
    await CartPanel.load({ keepMessage: true }); // e.g. show which item became unavailable
  } finally {
    checkoutButton.disabled = false;
  }
});
