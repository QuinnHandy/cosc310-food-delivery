// Orders page and profile editing (#99).
(async function () {
  const order = (id, total) => ({ id, customer_id: 4, restaurant_id: 1, restaurant_name: "Golden Dragon",
    delivery_address: "123 Main St", items: [{ menu_item_id: 1, name: "Kung Pao", unit_price: 15.5, quantity: 1, line_total: 15.5 }],
    subtotal: 15.5, delivery_fee: 4.99, total, status: "placed", created_at: "2026-11-20T01:02:03Z" });

  print("orders page, signed out");
  setPage("/orders");
  loadPage("app/static/orders.html"); load("app/static/api.js"); load("app/static/session.js"); load("app/static/order-view.js");
  routes["GET /customers/me/orders"] = () => [200, []];
  load("app/static/orders.js");
  await settle();
  check("signed-out user sent to sign in", window.location.href.startsWith("/account?next=%2Forders"), window.location.href);

  print("orders page, signed in");
  setPage("/orders");
  localStorage.setItem("authToken", "tok-c");
  localStorage.setItem("authSession", JSON.stringify({ email: "alice@x", role: "customer", user_id: 4 }));
  await loadOrders(); await settle();
  check("empty list message", document.getElementById("orders-status").textContent === "You have no orders yet.");

  routes["GET /customers/me/orders"] = () => [200, [order(2, 20.49), order(1, 35.99)]];
  routes["GET /orders/2"] = () => [200, order(2, 20.49)];
  routes["GET /orders/1"] = () => [403, { detail: "You can only view your own orders" }];
  await loadOrders(); await settle();
  const list = document.getElementById("orders-list");
  check("two orders, in the API's order", list.children.length === 2 && list.buttons()[0].textContent.startsWith("Order #2"));
  check("summary shows API total and status", list.buttons()[0].textContent.includes("$20.49 - placed"));
  await list.buttons()[0].click(); await settle();
  check("detail shown", document.getElementById("order-detail").hidden === false);
  check("detail has the snapshot line", document.getElementById("order-detail-body").textContent.includes("Kung Pao - $15.50 x 1 = $15.50"));
  await list.buttons()[1].click(); await settle();
  check("403 shown", document.getElementById("orders-status").textContent === "You can only view your own orders");
  check("detail hidden after error", document.getElementById("order-detail").hidden === true);

  done();
})();
