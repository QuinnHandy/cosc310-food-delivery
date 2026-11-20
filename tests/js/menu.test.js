(async function () {
  setPage("/");
  routes["GET /restaurants"] = () => [200, [{ id: 1, name: "Pizza", cuisine: "Italian" }, { id: 2, name: "Empty", cuisine: "Greek" }, { id: 3, name: "Broken", cuisine: "X" }]];
  routes["GET /restaurants/1"] = () => [200, { id: 1, name: "Pizza", cuisine: "Italian" }];
  routes["GET /restaurants/2"] = () => [200, { id: 2, name: "Empty", cuisine: "Greek" }];
  routes["GET /restaurants/3"] = () => [200, { id: 3, name: "Broken", cuisine: "X" }];
  routes["GET /restaurants/1/menu"] = () => [200, { restaurant_id: 1, items: [
    { id: 1, restaurant_id: 1, name: "Margherita", description: "Basil", price: 16.9, is_available: true, category: "Pizza" },
    { id: 2, restaurant_id: 1, name: "Tiramisu", description: "", price: 7, is_available: false, category: "Desserts" }] }];
  routes["GET /restaurants/2/menu"] = () => [200, { restaurant_id: 2, items: [] }];
  routes["GET /restaurants/3/menu"] = () => [500, { detail: "Could not load menu data: boom" }];
  loadPage("app/static/index.html"); load("app/static/api.js"); load("app/static/session.js"); load("app/static/cart.js"); load("app/static/app.js");
  await settle();
  const list = document.getElementById("restaurant-list");
  check("restaurants listed", list.children.length === 3, list.children.length);

  await list.buttons("Pizza (Italian)")[0].click(); await settle();
  const menu = document.getElementById("menu-list");
  check("details shown", document.getElementById("details").hidden === false);
  check("two items", menu.children.length === 2, menu.children.length);
  check("price formatted", menu.children[0].textContent.includes("$16.90"), menu.children[0].textContent);
  check("description shown", menu.children[0].textContent.includes("Basil"));
  check("unavailable marked", menu.children[1].className.includes("unavailable") && menu.children[1].textContent.includes("unavailable"));

  await list.buttons("Empty (Greek)")[0].click(); await settle();
  check("empty message", document.getElementById("menu-status").textContent.includes("no menu items yet"));
  check("old items cleared", menu.children.length === 0);

  await list.buttons("Broken (X)")[0].click(); await settle();
  check("error message from API", document.getElementById("menu-status").textContent === "Could not load the menu: Could not load menu data: boom",
    document.getElementById("menu-status").textContent);
  done();
})();
