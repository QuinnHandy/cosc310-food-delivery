// Owner page: create a restaurant, or pick one and update it.
// The API object comes from api.js, which is loaded first.

const manageForm = document.getElementById("manage-form");
const manageTitle = document.getElementById("manage-title");
const manageName = document.getElementById("manage-name");
const manageCuisine = document.getElementById("manage-cuisine");
const manageSubmit = document.getElementById("manage-submit");
const manageCancel = document.getElementById("manage-cancel");
const manageStatus = document.getElementById("manage-status");
const listStatus = document.getElementById("list-status");
const listEl = document.getElementById("restaurant-list");

// null = the form creates a restaurant; a number = it updates that restaurant
let editingId = null;

function setAddMode() {
  editingId = null;
  manageForm.reset();
  manageTitle.textContent = "Add a restaurant";
  manageSubmit.textContent = "Add restaurant";
  manageCancel.hidden = true;
}

function setEditMode(restaurant) {
  editingId = restaurant.id;
  manageTitle.textContent = `Edit restaurant #${restaurant.id}`;
  manageName.value = restaurant.name;
  manageCuisine.value = restaurant.cuisine;
  manageSubmit.textContent = "Save changes";
  manageCancel.hidden = false;
  manageStatus.textContent = "";
  manageName.focus();
}

async function loadRestaurants() {
  listStatus.textContent = "Loading...";
  try {
    const restaurants = await API.getRestaurants();
    listEl.replaceChildren();
    listStatus.textContent = restaurants.length ? "" : "No restaurants yet.";
    for (const restaurant of restaurants) {
      const item = document.createElement("li");
      item.append(`#${restaurant.id} ${restaurant.name} (${restaurant.cuisine}) `);
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = "Edit";
      button.addEventListener("click", () => setEditMode(restaurant));
      item.appendChild(button);
      listEl.appendChild(item);
    }
  } catch (error) {
    listEl.replaceChildren();
    listStatus.textContent = error.message;
  }
}

manageCancel.addEventListener("click", () => {
  setAddMode();
  manageStatus.textContent = "";
});

manageForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = {
    name: manageName.value.trim(),
    cuisine: manageCuisine.value.trim(),
  };
  if (!data.name || !data.cuisine) {
    manageStatus.textContent = "Name and cuisine are required.";
    return;
  }

  manageSubmit.disabled = true;
  try {
    if (editingId === null) {
      const created = await API.createRestaurant(data);
      manageStatus.textContent = `Added "${created.name}" (ID ${created.id}).`;
    } else {
      const updated = await API.updateRestaurant(editingId, data);
      manageStatus.textContent = `Saved changes to "${updated.name}".`;
    }
    setAddMode();
    await loadRestaurants();
  } catch (error) {
    manageStatus.textContent = error.message;
  } finally {
    manageSubmit.disabled = false;
  }
});

loadRestaurants();