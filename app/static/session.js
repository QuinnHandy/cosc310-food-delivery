// Shows who is signed in, with a sign-out button, in the page's #session-bar.
// Loaded after api.js on every page.

function renderSessionBar() {
  const bar = document.getElementById("session-bar");
  if (!bar) return;
  bar.replaceChildren();

  const session = Auth.session();
  if (!Auth.token() || !session) {
    const link = document.createElement("a");
    const next = window.location.pathname + window.location.search;
    link.href = `/account?${new URLSearchParams({ next })}`;
    link.textContent = "Sign in or register";
    bar.append("Not signed in. ", link);
    return;
  }

  bar.append(`Signed in as ${session.email} (${session.role}). `);
  const account = document.createElement("a");
  account.href = "/account";
  account.textContent = "My account";
  const signOut = document.createElement("button");
  signOut.type = "button";
  signOut.id = "sign-out";
  signOut.textContent = "Sign out";
  signOut.addEventListener("click", async () => {
    signOut.disabled = true;
    try {
      await API.logout();
    } catch (error) {
      // already signed out locally; the token was cleared either way
    }
    window.location.href = "/account?message=" + encodeURIComponent("You have signed out.");
  });
  bar.append(account, " ");
  if (session.role === "customer") {
    const orders = document.createElement("a");
    orders.href = "/orders";
    orders.textContent = "My orders";
    bar.append(orders, " ");
  }
  bar.append(signOut);
}

renderSessionBar();
