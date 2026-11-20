// Account page: sign in and register.
// The API and Auth objects come from api.js, which is loaded first.

const params = new URLSearchParams(window.location.search);
const messageEl = document.getElementById("account-message");
if (params.get("message")) messageEl.textContent = params.get("message");

// Where to go after signing in. `next` is parsed the way the browser will read it, and only
// followed if it stays on this site, so a crafted link like "/\evil.example" (browsers treat
// "\" as "/") or "//evil.example" cannot send the user to another website.
function nextPage(role, next = params.get("next")) {
  const fallback = role === "customer" ? "/" : "/owner";
  if (!next) return fallback;
  try {
    const url = new URL(next, window.location.origin);
    if (url.origin === window.location.origin && !url.pathname.startsWith("/account")) {
      return url.pathname + url.search + url.hash;
    }
  } catch (error) {
    // not a URL the browser could follow either
  }
  return fallback;
}

// ---- Sign in ----
const signinForm = document.getElementById("signin-form");
const signinStatus = document.getElementById("signin-status");
const signinSubmit = document.getElementById("signin-submit");

signinForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const email = document.getElementById("signin-email").value.trim();
  const password = document.getElementById("signin-password").value;
  signinSubmit.disabled = true;
  signinStatus.textContent = "Signing in...";
  try {
    const login = await API.login(email, password);
    window.location.href = nextPage(login.role);
  } catch (error) {
    signinStatus.textContent = error.message; // e.g. "Invalid email or password" (401)
  } finally {
    signinSubmit.disabled = false;
  }
});

// ---- Register ----
const registerForm = document.getElementById("register-form");
const registerStatus = document.getElementById("register-status");
const registerSubmit = document.getElementById("register-submit");

registerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = {
    name: document.getElementById("register-name").value.trim(),
    email: document.getElementById("register-email").value.trim(),
    password: document.getElementById("register-password").value,
  };
  const phone = document.getElementById("register-phone").value.trim();
  const address = document.getElementById("register-address").value.trim();
  if (phone) data.phone = phone;
  if (address) data.delivery_address = address;

  registerSubmit.disabled = true;
  registerStatus.textContent = "Creating your account...";
  try {
    await API.register(data); // 409 if the email is taken, 422 for invalid fields
    const login = await API.login(data.email, data.password);
    window.location.href = nextPage(login.role);
  } catch (error) {
    registerStatus.textContent = error.message;
  } finally {
    registerSubmit.disabled = false;
  }
});
