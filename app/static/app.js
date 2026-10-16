// All calls to the backend live in this one section.
const API = {
  async getRestaurants() {
    const response = await fetch("/restaurants");
    if (!response.ok) throw new Error("Could not load restaurants");
    return response.json();
  },
  async getRestaurant(id) {
    const response = await fetch(`/restaurants/${id}`);
    if (response.status === 404) throw new Error("Restaurant not found");
    if (!response.ok) throw new Error("Could not load restaurant details");
    return response.json();
  },
};

const statusEl = document.getElementById("status");
const listEl = document.getElementById("restaurant-list");
const detailsEl = document.getElementById("details");

async function showDetails(id) {
  statusEl.textContent = "";
  try {
    const restaurant = await API.getRestaurant(id);
    document.getElementById("details-name").textContent = restaurant.name;
    document.getElementById("details-cuisine").textContent = restaurant.cuisine;
    document.getElementById("details-id").textContent = restaurant.id;
    detailsEl.hidden = false;
  } catch (error) {
    detailsEl.hidden = true;
    statusEl.textContent = error.message;
  }
}

async function loadRestaurants() {
  statusEl.textContent = "Loading...";
  try {
    const restaurants = await API.getRestaurants();
    statusEl.textContent = restaurants.length ? "" : "No restaurants found.";
    for (const restaurant of restaurants) {
      const item = document.createElement("li");
      const button = document.createElement("button");
      button.textContent = `${restaurant.name} (${restaurant.cuisine})`;
      button.addEventListener("click", () => showDetails(restaurant.id));
      item.appendChild(button);
      listEl.appendChild(item);
    }
  } catch (error) {
    statusEl.textContent = error.message;
  }
}

loadRestaurants();