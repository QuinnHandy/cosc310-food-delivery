// Cart panel on the customer page (#98).
(async function () {
  const MENU = { restaurant_id: 1, items: [
    { id: 1, restaurant_id: 1, name: "Kung Pao", description: "", price: 15.5, is_available: true, category: "Mains" },
    { id: 3, restaurant_id: 1, name: "Chow Mein", description: "", price: 14.25, is_available: false, category: "Mains" },
  ] };
  // Deliberately odd totals: the page must show these exactly, not recompute them.
  const cartWith = (lines, totals) => ({ id: 7, customer_id: 4, restaurant_id: lines.length ? 1 : null, status: "active",
    items: lines, subtotal: totals[0], delivery_fee: totals[1], total: totals[2] });
  const LINE = { menu_item_id: 1, name: "Kung Pao", unit_price: 15.5, quantity: 2, line_total: 31, is_available: true };

  routes["GET /restaurants"] = () => [200, [{ id: 1, name: "Golden Dragon", cuisine: "Chinese" }]];
  routes["GET /restaurants/1"] = () => [200, { id: 1, name: "Golden Dragon", cuisine: "Chinese" }];
  routes["GET /restaurants/1/menu"] = () => [200, MENU];

  // ---- signed out ----
  setPage("/");
  loadPage("app/static/index.html"); load("app/static/api.js"); load("app/static/session.js"); load("app/static/cart.js"); load("app/static/app.js");
  await settle();
  print("signed out");
  check("asks to sign in", document.getElementById("cart-status").textContent === "Sign in as a customer to start a cart.");
  check("no cart request without a token", !calls.some((c) => c.path === "/cart"));
  await document.getElementById("restaurant-list").buttons()[0].click(); await settle();
  const menu = document.getElementById("menu-list");
  const addButtons = menu.buttons("Add to cart");
  check("every item has an add button", addButtons.length === 2, addButtons.length);
  check("unavailable item's button is disabled", addButtons[1].disabled === true && addButtons[0].disabled === false);
  await addButtons[0].click(); await settle();
  check("add while signed out goes to sign-in", window.location.href.startsWith("/account?next=%2F&message="), window.location.href);

  // ---- signed in as a customer ----
  setPage("/");
  localStorage.setItem("authToken", "tok-c");
  localStorage.setItem("authSession", JSON.stringify({ email: "alice@x", role: "customer", user_id: 4 }));
  let current = cartWith([], [0, 0, 0]);
  routes["GET /cart"] = () => [200, current];
  routes["POST /cart/items"] = (init) => {
    const body = JSON.parse(init.body);
    if (body.menu_item_id === 4) return [409, { detail: "Your cart can only contain items from one restaurant. Clear it or remove those items first." }];
    current = cartWith([LINE], [31, 4.99, 99.99]);
    return [200, current];
  };
  await CartPanel.load(); await settle();
  print("signed in");
  check("empty cart message", document.getElementById("cart-status").textContent === "Your cart is empty.");
  check("totals shown for empty cart", document.getElementById("cart-total").textContent === "$0.00");

  await addButtons[0].click(); await settle();
  const post = calls.filter((c) => c.path === "/cart/items" && c.method === "POST").pop();
  check("POST sends item id and quantity 1, no price", JSON.stringify(post.body) === '{"menu_item_id":1,"quantity":1}', post.body);
  check("POST sends the token", post.headers.Authorization === "Bearer tok-c");
  check("line rendered", document.getElementById("cart-list").children.length === 1);
  check("line shows API line total", document.getElementById("cart-list").children[0].textContent.includes("= $31.00"));
  check("subtotal from API", document.getElementById("cart-subtotal").textContent === "$31.00");
  check("fee from API", document.getElementById("cart-delivery-fee").textContent === "$4.99");
  check("total shown exactly as API sent it (not recomputed)", document.getElementById("cart-total").textContent === "$99.99");
  check("success message", document.getElementById("cart-status").textContent === "Added Kung Pao to your cart.");
  check("clear button shown", document.getElementById("cart-clear").hidden === false);

  print("API refusals are shown");
  await CartPanel.add({ id: 4, name: "Curry" }); await settle();
  check("409 message shown", document.getElementById("cart-status").textContent.includes("one restaurant"),
    document.getElementById("cart-status").textContent);
  check("cart still shown after refusal", document.getElementById("cart-list").children.length === 1);

  print("quantity, remove, clear");
  routes["PATCH /cart/items/1"] = (init) => {
    const q = JSON.parse(init.body).quantity;
    if (!Number.isInteger(q) || q < 1 || q > 20) return [422, { detail: [{ loc: ["body", "quantity"], msg: "Input should be less than or equal to 20" }] }];
    current = cartWith([{ ...LINE, quantity: q, line_total: 15.5 * q }], [15.5 * q, 4.99, 15.5 * q + 4.99]);
    return [200, current];
  };
  const qty = document.getElementById("cart-list").findAll((c) => c.tagName === "INPUT")[0];
  qty.value = "3"; await qty.dispatch("change"); await settle();
  const patch = calls.filter((c) => c.method === "PATCH").pop();
  check("PATCH sends a number", patch.body.quantity === 3, patch.body);
  check("new line total shown", document.getElementById("cart-list").children[0].textContent.includes("= $46.50"));

  const qty2 = document.getElementById("cart-list").findAll((c) => c.tagName === "INPUT")[0];
  qty2.value = "25"; await qty2.dispatch("change"); await settle();
  check("422 shown readably", document.getElementById("cart-status").textContent === "quantity: Input should be less than or equal to 20",
    document.getElementById("cart-status").textContent);
  check("cart reloaded to the stored quantity", document.getElementById("cart-list").findAll((c) => c.tagName === "INPUT")[0].value === "3");

  routes["DELETE /cart/items/1"] = () => { current = cartWith([], [0, 0, 0]); return [200, current]; };
  await document.getElementById("cart-list").buttons("Remove")[0].click(); await settle();
  check("remove sends DELETE for that item", calls.some((c) => c.method === "DELETE" && c.path === "/cart/items/1"));
  check("cart empty after remove", document.getElementById("cart-list").children.length === 0);

  current = cartWith([LINE], [31, 4.99, 35.99]);
  await CartPanel.load(); await settle();
  routes["DELETE /cart/items"] = () => { current = cartWith([], [0, 0, 0]); return [200, current]; };
  await document.getElementById("cart-clear").click(); await settle();
  check("clear sends DELETE /cart/items", calls.some((c) => c.method === "DELETE" && c.path === "/cart/items"));
  check("cleared", document.getElementById("cart-status").textContent === "Your cart is empty.");

  print("unavailable line flagged");
  current = cartWith([{ ...LINE, is_available: false }], [31, 4.99, 35.99]);
  await CartPanel.load(); await settle();
  check("flagged", document.getElementById("cart-list").children[0].textContent.includes("no longer available"));

  print("deactivated account");
  routes["GET /cart"] = () => [403, { detail: "This account has been deactivated" }];
  await CartPanel.load(); await settle();
  check("403 message shown", document.getElementById("cart-status").textContent === "This account has been deactivated");

  print("owner is not offered a cart");
  localStorage.setItem("authSession", JSON.stringify({ email: "o@x", role: "restaurant_owner", user_id: 2 }));
  await CartPanel.load(); await settle();
  check("owner sees sign-in-as-customer message", document.getElementById("cart-status").textContent === "Sign in as a customer to start a cart.");

  done();
})();
