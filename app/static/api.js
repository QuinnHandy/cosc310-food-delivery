// Shared by the customer page and the owner page.
// All calls to the backend live in this one file.

// The sign-in token the owner page sends with every change.
// TODO(#97): the sign-in page should save the token from POST /auth/login under this key.
// Until it exists, paste one in the browser console:
//   localStorage.setItem("authToken", "<token>")
const TOKEN_KEY = "authToken";

function authHeaders() {
  try {
    const token = localStorage.getItem(TOKEN_KEY);
    return token ? { Authorization: `Bearer ${token}` } : {};
  } catch (error) {
    return {}; // storage is blocked, so the request goes without a token and the API answers 401
  }
}

// Turns an error response from the API into a readable message.
// 401/403 and 404 errors send detail as text; 422 validation errors send it as a list.
async function errorMessage(response, fallback) {
  if (response.status === 401) return "Please sign in as a restaurant owner first.";
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail
        .map((d) => `${d.loc.slice(1).join(".")}: ${d.msg}`)
        .join("; ");
    }
  } catch (error) {
    // response had no JSON body, use the fallback below
  }
  return fallback;
}

const API = {
  async getRestaurants(filters = {}) {
    const params = new URLSearchParams();
    if (filters.name) params.set("name", filters.name);
    if (filters.cuisine) params.set("cuisine", filters.cuisine);
    const query = params.toString();
    const response = await fetch(query ? `/restaurants?${query}` : "/restaurants");
    if (!response.ok) throw new Error("Could not load restaurants");
    return response.json();
  },
  async getRestaurant(id) {
    const response = await fetch(`/restaurants/${id}`);
    if (response.status === 404) throw new Error("Restaurant not found");
    if (!response.ok) throw new Error("Could not load restaurant details");
    return response.json();
  },
  async createRestaurant(data) {
    const response = await fetch("/restaurants", {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      throw new Error(await errorMessage(response, "Could not create restaurant"));
    }
    return response.json();
  },
  async updateRestaurant(id, data) {
    const response = await fetch(`/restaurants/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      throw new Error(await errorMessage(response, "Could not update restaurant"));
    }
    return response.json();
  },
};