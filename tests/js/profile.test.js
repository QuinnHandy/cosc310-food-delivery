// Profile section on the account page (#99).
(async function () {
  setPage("/account");
  localStorage.setItem("authToken", "tok-c");
  localStorage.setItem("authSession", JSON.stringify({ email: "alice@x", role: "customer", user_id: 4 }));
  let profile = { id: 4, email: "alice@x", name: "Alice", phone: "", delivery_address: "", is_active: true };
  routes["GET /customers/me"] = () => [200, profile];
  routes["PATCH /customers/me"] = (init) => {
    const body = JSON.parse(init.body);
    if (body.delivery_address === "") return [422, { detail: [{ loc: ["body", "delivery_address"], msg: "Value error, Must not be empty." }] }];
    profile = { ...profile, ...body };
    return [200, profile];
  };
  loadPage("app/static/account.html"); load("app/static/api.js"); load("app/static/session.js"); load("app/static/account.js");
  await settle();

  check("profile shown for a signed-in customer", document.getElementById("profile-section").hidden === false);
  check("sign-in form hidden", document.getElementById("signin-section").hidden === true);
  check("fields filled from the API", document.getElementById("profile-name").value === "Alice");

  await document.getElementById("profile-form").submit(); await settle();
  check("nothing changed, nothing sent", !calls.some((c) => c.method === "PATCH") &&
    document.getElementById("profile-status").textContent === "Nothing to save.");

  document.getElementById("profile-address").value = " 9 New Rd ";
  await document.getElementById("profile-form").submit(); await settle();
  const patch = calls.filter((c) => c.method === "PATCH").pop();
  check("only the changed field is sent, trimmed", JSON.stringify(patch.body) === '{"delivery_address":"9 New Rd"}', patch.body);
  check("saved message", document.getElementById("profile-status").textContent === "Saved.");

  document.getElementById("profile-address").value = "";
  await document.getElementById("profile-form").submit(); await settle();
  check("422 shown", document.getElementById("profile-status").textContent === "delivery_address: Value error, Must not be empty.",
    document.getElementById("profile-status").textContent);

  done();
})();
