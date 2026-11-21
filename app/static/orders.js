// Orders page (#99): the signed-in customer's orders, newest first as the API returns them,
// and the details of one order when it is clicked.

const ordersStatusEl = document.getElementById("orders-status");
const ordersListEl = document.getElementById("orders-list");
const orderDetailEl = document.getElementById("order-detail");
const orderDetailBodyEl = document.getElementById("order-detail-body");

async function showOrder(orderId) {
  ordersStatusEl.textContent = "";
  try {
    const order = await API.getOrder(orderId);
    orderDetailBodyEl.replaceChildren(orderDetailsElement(order));
    orderDetailEl.hidden = false;
  } catch (error) {
    if (error.status === 401) return;
    orderDetailEl.hidden = true;
    ordersStatusEl.textContent = error.message; // e.g. 403 for someone else's order, 404
  }
}

async function loadOrders() {
  if (!Auth.token()) {
    Auth.goToSignIn("Sign in to see your orders.");
    return;
  }
  ordersStatusEl.textContent = "Loading...";
  try {
    const orders = await API.getMyOrders();
    ordersListEl.replaceChildren();
    ordersStatusEl.textContent = orders.length ? "" : "You have no orders yet.";
    for (const order of orders) {
      const item = document.createElement("li");
      const button = document.createElement("button");
      button.type = "button";
      button.textContent =
        `Order #${order.id} - ${order.restaurant_name || `Restaurant ${order.restaurant_id}`} - ` +
        `${orderMoney(order.total)} - ${order.status} - ${orderDate(order.created_at)}`;
      button.addEventListener("click", () => showOrder(order.id));
      item.appendChild(button);
      ordersListEl.appendChild(item);
    }
  } catch (error) {
    if (error.status === 401) return;
    ordersListEl.replaceChildren();
    ordersStatusEl.textContent = error.message;
  }
}

loadOrders();
