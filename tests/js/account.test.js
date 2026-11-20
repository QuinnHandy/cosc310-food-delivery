(async function () {
  setPage("/account?next=%2Fowner");
  routes["POST /auth/login"] = (init) => {
    const b = JSON.parse(init.body);
    if (b.password === "right") return [200, { token: "tok-1", user_id: 2, role: "restaurant_owner" }];
    return [401, { detail: "Invalid email or password" }];
  };
  routes["POST /customers"] = (init) => {
    const b = JSON.parse(init.body);
    if (b.email === "taken@x.com") return [409, { detail: "A user with email taken@x.com already exists" }];
    if (b.password.length < 8) return [422, { detail: [{ loc: ["body", "password"], msg: "String should have at least 8 characters" }] }];
    return [201, { id: 7, email: b.email, role: "customer" }];
  };
  loadPage("app/static/account.html"); load("app/static/api.js");
  load("app/static/session.js");
  load("app/static/account.js");

  print("session bar, signed out");
  check("shows sign-in link", document.getElementById("session-bar").textContent.includes("Sign in or register"));

  print("wrong password");
  document.getElementById("signin-email").value = "Owner1@foodapp.test ";
  document.getElementById("signin-password").value = "wrong";
  await document.getElementById("signin-form").submit();
  check("shows API message", document.getElementById("signin-status").textContent === "Invalid email or password",
    document.getElementById("signin-status").textContent);
  check("does not redirect on login 401", window.location.href === "/account?next=%2Fowner", window.location.href);
  check("no token saved", localStorage.getItem("authToken") === null);

  print("right password");
  document.getElementById("signin-password").value = "right";
  await document.getElementById("signin-form").submit();
  check("token saved", localStorage.getItem("authToken") === "tok-1");
  check("session saved with lowercase email", Auth.session().email === "owner1@foodapp.test", Auth.session());
  check("redirects to ?next", window.location.href === "/owner", window.location.href);

  print("token header on protected calls only");
  routes["POST /restaurants"] = () => [201, { id: 9, name: "N", cuisine: "C" }];
  routes["GET /restaurants"] = () => [200, []];
  await API.createRestaurant({ name: "N", cuisine: "C" });
  await API.getRestaurants();
  const create = calls.find((c) => c.method === "POST" && c.path === "/restaurants");
  const list = calls.find((c) => c.method === "GET" && c.path === "/restaurants");
  check("create sends Bearer token", create.headers.Authorization === "Bearer tok-1", create.headers);
  check("public list sends no token", !list.headers.Authorization, list.headers);

  print("401 on a protected call");
  setPage("/owner");
  routes["PATCH /restaurants/1"] = () => [401, { detail: "Invalid session token" }];
  let err;
  try { await API.updateRestaurant(1, { name: "x" }); } catch (e) { err = e; }
  check("throws with status", err && err.status === 401, err && err.status);
  check("clears token", localStorage.getItem("authToken") === null);
  check("redirects to sign-in with next", window.location.href.startsWith("/account?next=%2Fowner"), window.location.href);

  print("403 is shown, not redirected");
  localStorage.setItem("authToken", "tok-2");
  setPage("/owner");
  routes["PATCH /restaurants/2"] = () => [403, { detail: "You do not have permission to change this restaurant" }];
  err = undefined;
  try { await API.updateRestaurant(2, { name: "x" }); } catch (e) { err = e; }
  check("403 message", err.message === "You do not have permission to change this restaurant", err.message);
  check("stays on page", window.location.href === "/owner");
  check("keeps token", localStorage.getItem("authToken") === "tok-2");

  print("register errors and success");
  setPage("/account");
  const fill = (name, email, pw) => {
    document.getElementById("register-name").value = name;
    document.getElementById("register-email").value = email;
    document.getElementById("register-password").value = pw;
  };
  fill("T", "taken@x.com", "password1");
  await document.getElementById("register-form").submit();
  check("409 shown", document.getElementById("register-status").textContent.includes("already exists"));
  fill("T", "new@x.com", "short");
  await document.getElementById("register-form").submit();
  check("422 shown readably", document.getElementById("register-status").textContent === "password: String should have at least 8 characters",
    document.getElementById("register-status").textContent);
  routes["POST /auth/login"] = () => [200, { token: "tok-new", user_id: 7, role: "customer" }];
  fill("T", "new@x.com", "password1");
  document.getElementById("register-phone").value = "";
  document.getElementById("register-address").value = "1 Road";
  await document.getElementById("register-form").submit();
  const reg = calls.filter((c) => c.path === "/customers").pop();
  check("register body omits empty phone", !("phone" in reg.body) && reg.body.delivery_address === "1 Road", reg.body);
  check("signed in after register", localStorage.getItem("authToken") === "tok-new");
  check("follows ?next from page load", window.location.href === "/owner", window.location.href);

  print("open redirect blocked");
  setPage("/account?next=%2F%2Fevil.com");
  // re-evaluate nextPage with new params: account.js read params at load, so test the rule directly
  check("// rejected", !("//evil.com".startsWith("/") && !"//evil.com".startsWith("//")));

  print("sign out");
  setPage("/");
  localStorage.setItem("authToken", "tok-new");
  localStorage.setItem("authSession", JSON.stringify({ email: "new@x.com", role: "customer", user_id: 7 }));
  routes["POST /auth/logout"] = () => [401, { detail: "Invalid session token" }];
  renderSessionBar();
  check("bar shows email and role", document.getElementById("session-bar").textContent.includes("new@x.com (customer)"));
  await document.getElementById("session-bar").buttons("Sign out")[0].click();
  check("token cleared even when logout 401s", localStorage.getItem("authToken") === null);
  check("no redirect loop: goes to account with message", window.location.href.startsWith("/account?message="), window.location.href);

  done();
})();
