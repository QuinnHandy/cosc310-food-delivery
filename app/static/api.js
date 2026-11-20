// Shared by every page. All calls to the backend live in this one file.
//
// Signing in (account page) saves the token from POST /auth/login, and every request made
// through `request` sends it as `Authorization: Bearer <token>`. The backend decides what each
// user may do; this file only passes the token along and shows the API's error messages.

const TOKEN_KEY = "authToken";
const SESSION_KEY = "authSession"; // {email, role, user_id}, only used to show who is signed in

// localStorage can be blocked (private mode, strict settings). Then the user just looks
// signed out and the API answers 401, which the page reports.
function storageGet(key) {
  try {
    return localStorage.getItem(key);
  } catch (error) {
    return null;
  }
}

function storageSet(key, value) {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch (error) {
    // nothing to do: see storageGet
  }
}

const Auth = {
  token() {
    return storageGet(TOKEN_KEY);
  },
  // {email, role, user_id} for the signed-in user, or null.
  session() {
    try {
      return JSON.parse(storageGet(SESSION_KEY)) || null;
    } catch (error) {
      return null;
    }
  },
  save(login, email) {
    storageSet(TOKEN_KEY, login.token);
    storageSet(SESSION_KEY, JSON.stringify({ email, role: login.role, user_id: login.user_id }));
  },
  clear() {
    storageSet(TOKEN_KEY, null);
    storageSet(SESSION_KEY, null);
  },
  // Sends the user to the account page, then back to this page after signing in.
  goToSignIn(message) {
    const next = window.location.pathname + window.location.search;
    const params = new URLSearchParams({ next });
    if (message) params.set("message", message);
    window.location.href = `/account?${params}`;
  },
};

function authHeaders() {
  const token = Auth.token();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// Turns an error response from the API into a readable message.
// 401/403/404/409 errors send detail as text; 422 validation errors send it as a list.
async function errorMessage(response, fallback) {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail
        .map((d) => `${d.loc.slice(1).join(".") || "request"}: ${d.msg}`)
        .join("; ");
    }
  } catch (error) {
    // response had no JSON body, use the fallback below
  }
  return fallback;
}

// An error from the API, with its HTTP status so a page can react to specific codes.
class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

// Sends one request and returns the parsed JSON body (or null for 204).
// options.auth: send the token. A 401 then means the session is gone, so the token is
//   cleared and the user is sent to sign in (unless options.redirectOn401 is false).
// options.fallback: message to show if the API gives no detail.
async function request(method, path, { body, auth = false, redirectOn401 = true, fallback } = {}) {
  const headers = auth ? authHeaders() : {};
  const init = { method, headers };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(path, init);
  } catch (error) {
    throw new ApiError("Could not reach the server. Is it running?", 0);
  }

  if (response.ok) {
    return response.status === 204 ? null : response.json();
  }
  const message = await errorMessage(response, fallback || `Request failed (${response.status})`);
  if (response.status === 401 && auth && redirectOn401) {
    Auth.clear();
    Auth.goToSignIn("Your session has ended. Please sign in again.");
  }
  throw new ApiError(message, response.status);
}

const API = {
  // ---- Restaurants and menus (public) ----
  getRestaurants(filters = {}) {
    const params = new URLSearchParams();
    if (filters.name) params.set("name", filters.name);
    if (filters.cuisine) params.set("cuisine", filters.cuisine);
    const query = params.toString();
    return request("GET", query ? `/restaurants?${query}` : "/restaurants", {
      fallback: "Could not load restaurants",
    });
  },
  getRestaurant(id) {
    return request("GET", `/restaurants/${id}`, {
      fallback: "Could not load restaurant details",
    });
  },
  getMenu(restaurantId) {
    return request("GET", `/restaurants/${restaurantId}/menu`, {
      fallback: "Could not load the menu",
    });
  },

  // ---- Restaurant management (owner or admin) ----
  createRestaurant(data) {
    return request("POST", "/restaurants", {
      body: data,
      auth: true,
      fallback: "Could not create restaurant",
    });
  },
  updateRestaurant(id, data) {
    return request("PATCH", `/restaurants/${id}`, {
      body: data,
      auth: true,
      fallback: "Could not update restaurant",
    });
  },

  // ---- Accounts ----
  // A wrong password is a 401 too, so sign-in shows the message instead of redirecting.
  async login(email, password) {
    const login = await request("POST", "/auth/login", {
      body: { email, password },
      fallback: "Could not sign in",
    });
    Auth.save(login, email.trim().toLowerCase());
    return login;
  },
  async logout() {
    try {
      await request("POST", "/auth/logout", { auth: true, redirectOn401: false });
    } finally {
      Auth.clear(); // signed out locally even if the session had already ended
    }
  },
  register(data) {
    return request("POST", "/customers", { body: data, fallback: "Could not register" });
  },
};
