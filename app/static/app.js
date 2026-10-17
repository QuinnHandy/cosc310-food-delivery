// Customer page: restaurant list, details, and search.
// The API object comes from api.js, which is loaded first.

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

let latestRequest = 0;

async function loadRestaurants(filters = {}) {
  const requestId = ++latestRequest;
  statusEl.textContent = "Loading...";
  detailsEl.hidden = true;
  try {
    const restaurants = await API.getRestaurants(filters);
    if (requestId !== latestRequest) return; // a newer search has started, ignore this one
    listEl.replaceChildren();
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
    if (requestId !== latestRequest) return;
    listEl.replaceChildren();
    statusEl.textContent = error.message;
  }
}

const formEl = document.getElementById("search-form");
const nameInput = document.getElementById("search-name");
const cuisineInput = document.getElementById("search-cuisine");

function currentFilters() {
  return {
    name: nameInput.value.trim(),
    cuisine: cuisineInput.value.trim(),
  };
}

let debounceTimer;
function searchSoon() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => loadRestaurants(currentFilters()), 300);
}

nameInput.addEventListener("input", searchSoon);
cuisineInput.addEventListener("change", searchSoon);

formEl.addEventListener("submit", (event) => {
  event.preventDefault();
  clearTimeout(debounceTimer);
  loadRestaurants(currentFilters());
});

document.getElementById("search-clear").addEventListener("click", () => {
  clearTimeout(debounceTimer);
  formEl.reset();
  loadRestaurants();
});

// Fills the cuisine dropdown from the API. The API matches cuisine ignoring
// case, so "italian" and "Italian" are shown once.
async function loadCuisines() {
  try {
    const all = await API.getRestaurants();
    const byKey = new Map();
    for (const restaurant of all) {
      const key = restaurant.cuisine.toLowerCase();
      if (!byKey.has(key)) byKey.set(key, restaurant.cuisine);
    }
    const cuisines = [...byKey.values()].sort((a, b) => a.localeCompare(b));
    cuisineInput.replaceChildren(new Option("All cuisines", ""));
    for (const cuisine of cuisines) {
      cuisineInput.appendChild(new Option(cuisine, cuisine));
    }
  } catch (error) {
    // the main list load shows an error message if the API is down
  }
}

loadCuisines();
loadRestaurants();