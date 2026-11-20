// Shows one order (#99), as returned by POST /checkout and GET /orders/{id}.
// Used by the checkout confirmation on the customer page and by the orders page.
// Every amount is the order's stored snapshot from the API; nothing is recalculated here.

function orderMoney(amount) {
  return `$${Number(amount).toFixed(2)}`;
}

function orderDate(createdAt) {
  const date = new Date(createdAt);
  return Number.isNaN(date.getTime()) ? String(createdAt || "") : date.toLocaleString();
}

// Returns an element with the order's ID, status, restaurant, address, lines and totals.
function orderDetailsElement(order) {
  const box = document.createElement("div");
  box.className = "order-details";

  const heading = document.createElement("h3");
  heading.textContent = `Order #${order.id} - ${order.status}`;
  box.appendChild(heading);

  const meta = document.createElement("p");
  meta.textContent =
    `${order.restaurant_name || `Restaurant ${order.restaurant_id}`}, placed ${orderDate(order.created_at)}. ` +
    `Delivering to: ${order.delivery_address}`;
  box.appendChild(meta);

  const lines = document.createElement("ul");
  for (const line of order.items) {
    const item = document.createElement("li");
    item.textContent =
      `${line.name} - ${orderMoney(line.unit_price)} x ${line.quantity} = ${orderMoney(line.line_total)}`;
    lines.appendChild(item);
  }
  box.appendChild(lines);

  const totals = document.createElement("p");
  totals.textContent =
    `Subtotal ${orderMoney(order.subtotal)}, delivery ${orderMoney(order.delivery_fee)}, ` +
    `total ${orderMoney(order.total)}`;
  box.appendChild(totals);
  return box;
}
