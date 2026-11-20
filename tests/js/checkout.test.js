// Checkout, orders page and profile (#99).
(async function () {
  const LINE = { menu_item_id: 1, name: "Kung Pao", unit_price: 15.5, quantity: 2, line_total: 31, is_available: true };
  const cart = (items) => ({ id: 7, customer_id: 4, restaurant_id: items.length ? 1 : null, status: "active",
    items, subtotal: items.length ? 31 : 0, delivery_fee: items.length ? 4.99 : 0, total: items.length ? 35.99 : 0 });
  const ORDER = { id: 12, customer_id: 4, restaurant_id: 1, restaurant_name: "Golden Dragon", delivery_address: "123 Main St",
    items: [{ menu_item_id: 1, name: "Kung Pao", unit_price: 15.5, quantity: 2, line_total: 31 }],
    subtotal: 31, delivery_fee: 4.99, total: 35.99, status: "placed", created_at: "2026-11-20T01:02:03Z" };

  routes["GET /restaurants"] = () => [200, []];
  setPage("/");
  localStorage.setItem("authToken", "tok-c");
  localStorage.setItem("authSession", JSON.stringify({ email: "alice@x", role: "customer", user_id: 4 }));
  let current = cart([LINE]);
  routes["GET /cart"] = () => [200, current];
  loadPage("app/static/index.html"); load("app/static/api.js"); load("app/static/session.js"); load("app/static/cart.js");
  load("app/static/order-view.js"); load("app/static/checkout.js"); load("app/static/app.js");
  await settle();
  const button = document.getElementById("cart-checkout");
  const status = document.getElementById("checkout-status");

  print("checkout button");
  check("shown when the cart has items", button.hidden === false);
  check("session bar links to My orders", document.getElementById("session-bar").textContent.includes("My orders"));

  print("refusals are shown with the API message");
  routes["POST /checkout"] = () => [409, { detail: "Kung Pao is no longer available" }];
  await button.click(); await settle();
  check("409 message", status.textContent === "Kung Pao is no longer available", status.textContent);
  check("no confirmation", document.getElementById("order-confirmation").hidden === true);

  routes["POST /checkout"] = () => [422, { detail: "Add a delivery address before checking out" }];
  await button.click(); await settle();
  check("422 address message", status.textContent.startsWith("Add a delivery address before checking out"));
  check("links to the account page", status.findAll((c) => c.href === "/account").length === 1);

  routes["POST /checkout"] = () => [403, { detail: "This account has been deactivated" }];
  await button.click(); await settle();
  check("403 message", status.textContent === "This account has been deactivated");

  print("successful checkout");
  routes["POST /checkout"] = () => { current = cart([]); return [201, ORDER]; };
  await button.click(); await settle();
  const post = calls.filter((c) => c.path === "/checkout").pop();
  check("POST /checkout has no body and sends the token", post.body === undefined && post.headers.Authorization === "Bearer tok-c");
  const confirmation = document.getElementById("order-confirmation-body").textContent;
  check("confirmation shown", document.getElementById("order-confirmation").hidden === false);
  check("shows order id and status", confirmation.includes("Order #12 - placed"), confirmation);
  check("shows the line", confirmation.includes("Kung Pao - $15.50 x 2 = $31.00"));
  check("shows API totals", confirmation.includes("total $35.99"));
  check("cart reloaded and empty", document.getElementById("cart-status").textContent === "Your cart is empty.");
  check("checkout button hidden for empty cart", button.hidden === true);
  check("status cleared", status.textContent === "");

  done();
})();
