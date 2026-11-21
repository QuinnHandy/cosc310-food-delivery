// The whole M2 demo flow through the real page scripts (#99):
// register → sign in → restaurant → menu → cart → checkout → order → My orders.
// The fake backend below keeps state between requests, like the real API, so each page sees
// what the previous one did. Moving to another page is setPage + loading that page's scripts.
(async function () {
  // ---- a tiny stateful fake of the API ----
  const db = { users: [], token: null, cart: [], orders: [] };
  const MENU = [
    { id: 1, restaurant_id: 1, name: "Kung Pao", description: "", price: 15.5, is_available: true, category: "Mains" },
    { id: 2, restaurant_id: 1, name: "Spring Rolls", description: "", price: 7, is_available: true, category: "Starters" },
  ];
  const authed = (init) => init.headers && init.headers.Authorization === `Bearer ${db.token}`;
  const priced = () => {
    const items = db.cart.map((l) => {
      const m = MENU.find((x) => x.id === l.menu_item_id);
      return { menu_item_id: m.id, name: m.name, unit_price: m.price, quantity: l.quantity, line_total: m.price * l.quantity, is_available: true };
    });
    const subtotal = items.reduce((s, l) => s + l.line_total, 0);
    const fee = items.length ? 4.99 : 0;
    return { id: 1, customer_id: 7, restaurant_id: items.length ? 1 : null, status: "active", items, subtotal, delivery_fee: fee, total: Math.round((subtotal + fee) * 100) / 100 };
  };
  routes["POST /customers"] = (init) => { const b = JSON.parse(init.body); db.users.push(b); return [201, { id: 7, email: b.email }]; };
  routes["POST /auth/login"] = (init) => {
    const b = JSON.parse(init.body);
    if (!db.users.some((u) => u.email === b.email && u.password === b.password)) return [401, { detail: "Invalid email or password" }];
    db.token = "tok-flow"; return [200, { token: db.token, user_id: 7, role: "customer" }];
  };
  routes["GET /restaurants"] = () => [200, [{ id: 1, name: "Golden Dragon", cuisine: "Chinese" }]];
  routes["GET /restaurants/1"] = () => [200, { id: 1, name: "Golden Dragon", cuisine: "Chinese" }];
  routes["GET /restaurants/1/menu"] = () => [200, { restaurant_id: 1, items: MENU }];
  routes["GET /cart"] = (init) => (authed(init) ? [200, priced()] : [401, { detail: "Not authenticated" }]);
  routes["POST /cart/items"] = (init) => {
    if (!authed(init)) return [401, { detail: "Not authenticated" }];
    const b = JSON.parse(init.body);
    const line = db.cart.find((l) => l.menu_item_id === b.menu_item_id);
    if (line) line.quantity += b.quantity; else db.cart.push({ menu_item_id: b.menu_item_id, quantity: b.quantity });
    return [200, priced()];
  };
  routes["POST /checkout"] = (init) => {
    if (!authed(init)) return [401, { detail: "Not authenticated" }];
    const c = priced();
    const order = { id: db.orders.length + 1, customer_id: 7, restaurant_id: 1, restaurant_name: "Golden Dragon",
      delivery_address: db.users[0].delivery_address, items: c.items.map(({ is_available, ...l }) => l),
      subtotal: c.subtotal, delivery_fee: c.delivery_fee, total: c.total, status: "placed", created_at: "2026-11-20T01:02:03Z" };
    db.orders.push(order); db.cart = [];
    return [201, order];
  };
  routes["GET /customers/me/orders"] = (init) => (authed(init) ? [200, db.orders.slice().reverse()] : [401, {}]);
  routes["GET /orders/1"] = (init) => (authed(init) ? [200, db.orders[0]] : [401, {}]);
  routes["GET /customers/me"] = () => [200, { id: 7, email: "dana@x.com", name: "Dana", phone: "", delivery_address: "1 Lake Rd", is_active: true }];

  // ---- 1. register on the account page (arriving from the home page) ----
  print("register and sign in");
  setPage("/account?next=%2F");
  loadPage("app/static/account.html"); load("app/static/api.js"); load("app/static/session.js"); load("app/static/account.js");
  document.getElementById("register-name").value = "Dana";
  document.getElementById("register-email").value = "dana@x.com";
  document.getElementById("register-password").value = "longenough";
  document.getElementById("register-address").value = "1 Lake Rd";
  await document.getElementById("register-form").submit(); await settle();
  check("signed in after registering", localStorage.getItem("authToken") === "tok-flow");
  check("sent back to the home page", window.location.href === "/", window.location.href);

  // ---- 2. home page: restaurant → menu → cart → checkout ----
  print("browse, add to cart, check out");
  setPage("/");
  loadPage("app/static/index.html"); renderSessionBar();
  load("app/static/cart.js"); load("app/static/order-view.js"); load("app/static/checkout.js"); load("app/static/app.js");
  await settle();
  check("session bar shows the new customer", document.getElementById("session-bar").textContent.includes("dana@x.com (customer)"));
  check("empty cart", document.getElementById("cart-status").textContent === "Your cart is empty.");
  await document.getElementById("restaurant-list").buttons()[0].click(); await settle();
  const adds = document.getElementById("menu-list").buttons("Add to cart");
  await adds[0].click(); await settle();
  await adds[0].click(); await settle();
  await adds[1].click(); await settle();
  check("cart has two lines", document.getElementById("cart-list").children.length === 2);
  check("total from the API", document.getElementById("cart-total").textContent === "$42.99", document.getElementById("cart-total").textContent);
  check("checkout button shown", document.getElementById("cart-checkout").hidden === false);
  await document.getElementById("cart-checkout").click(); await settle();
  const placed = document.getElementById("order-confirmation-body").textContent;
  check("order shown with id and status", placed.includes("Order #1 - placed"), placed);
  check("order total", placed.includes("total $42.99"));
  check("delivery address from registration", placed.includes("Delivering to: 1 Lake Rd"));
  check("cart is empty after checkout", document.getElementById("cart-status").textContent === "Your cart is empty.");

  // ---- 3. orders page ----
  print("my orders");
  setPage("/orders");
  loadPage("app/static/orders.html"); renderSessionBar(); load("app/static/orders.js");
  await settle();
  const orders = document.getElementById("orders-list");
  check("order listed", orders.children.length === 1 && orders.buttons()[0].textContent.includes("$42.99 - placed"));
  await orders.buttons()[0].click(); await settle();
  check("order details", document.getElementById("order-detail-body").textContent.includes("Kung Pao - $15.50 x 2 = $31.00"));

  done();
})();
