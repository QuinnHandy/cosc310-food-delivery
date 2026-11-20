// Minimal browser stand-in for running the static page scripts outside a browser.
// tests/test_frontend_js.py runs each tests/js/*.test.js file after this one, with Node
// (through run_node.js) or with macOS JavaScriptCore (jsc). Both run the files as plain
// scripts that share one global scope, like <script> tags on a page.
// In a test: setPage("/path?query"), add fetch stubs to `routes`, then load() page scripts.

var results = { pass: 0, fail: 0 };
function check(name, cond, extra) {
  if (cond) { results.pass++; print("  ok   " + name); }
  else { results.fail++; print("  FAIL " + name + (extra !== undefined ? "  -> " + JSON.stringify(extra) : "")); }
}

function defineGlobal(name, value) {
  Object.defineProperty(globalThis, name, { value, writable: true, configurable: true });
}

// ---- URLSearchParams (jsc has none; Node's is replaced so both engines behave the same) ----
function SimpleURLSearchParams(init) {
  this._p = [];
  if (typeof init === "string") {
    init.replace(/^\?/, "").split("&").filter(Boolean).forEach((kv) => {
      const i = kv.indexOf("=");
      const k = i < 0 ? kv : kv.slice(0, i);
      const v = i < 0 ? "" : kv.slice(i + 1);
      this._p.push([decodeURIComponent(k.replace(/\+/g, " ")), decodeURIComponent(v.replace(/\+/g, " "))]);
    });
  } else if (init && typeof init === "object") {
    Object.keys(init).forEach((k) => this._p.push([k, String(init[k])]));
  }
}
SimpleURLSearchParams.prototype.get = function (k) { const e = this._p.find((p) => p[0] === k); return e ? e[1] : null; };
SimpleURLSearchParams.prototype.set = function (k, v) { this._p = this._p.filter((p) => p[0] !== k); this._p.push([k, String(v)]); };
SimpleURLSearchParams.prototype.toString = function () { return this._p.map((p) => encodeURIComponent(p[0]) + "=" + encodeURIComponent(p[1])).join("&"); };

// ---- fake DOM ----
function El(tag, id) {
  this.tagName = (tag || "div").toUpperCase(); this.id = id || ""; this.children = [];
  this._text = ""; this.value = ""; this.hidden = false; this.disabled = false; this.className = "";
  this.type = ""; this.href = ""; this._listeners = {}; this.dataset = {}; this.checked = false;
}
Object.defineProperty(El.prototype, "textContent", {
  get() { return this._text + this.children.map((c) => (typeof c === "string" ? c : c.textContent)).join(""); },
  set(v) { this._text = String(v); this.children = []; },
});
El.prototype.append = function (...nodes) { nodes.forEach((n) => this.children.push(n)); };
El.prototype.appendChild = function (n) { this.children.push(n); return n; };
El.prototype.replaceChildren = function (...nodes) { this._text = ""; this.children = nodes.slice(); };
El.prototype.addEventListener = function (type, fn) { (this._listeners[type] = this._listeners[type] || []).push(fn); };
El.prototype.dispatch = async function (type) {
  const event = { type, target: this, preventDefault() {} };
  for (const fn of this._listeners[type] || []) await fn(event);
};
El.prototype.click = function () { return this.dispatch("click"); };
El.prototype.submit = function () { return this.dispatch("submit"); };
El.prototype.reset = function () {};
El.prototype.focus = function () {};
// Depth-first search of created children, for buttons the scripts build.
El.prototype.findAll = function (pred, out) {
  out = out || [];
  for (const c of this.children) { if (typeof c !== "string") { if (pred(c)) out.push(c); c.findAll(pred, out); } }
  return out;
};
El.prototype.buttons = function (text) { return this.findAll((c) => c.tagName === "BUTTON" && (!text || c.textContent === text)); };

var elements = {};
var fakeDocument = {
  getElementById(id) { return elements[id] || (elements[id] = new El("div", id)); },
  createElement(tag) { return new El(tag); },
};
defineGlobal("URLSearchParams", SimpleURLSearchParams);
defineGlobal("document", fakeDocument);
function Option(text, value) { const o = new El("option"); o.textContent = text; o.value = value; return o; }

// ---- window, storage, timers ----
defineGlobal("window", { location: { pathname: "/", search: "", href: "/" } });
function setPage(url) {
  const i = url.indexOf("?");
  window.location.pathname = i < 0 ? url : url.slice(0, i);
  window.location.search = i < 0 ? "" : url.slice(i);
  window.location.href = url;
}
var storage = {};
var fakeStorage = {
  getItem(k) { return Object.prototype.hasOwnProperty.call(storage, k) ? storage[k] : null; },
  setItem(k, v) { storage[k] = String(v); },
  removeItem(k) { delete storage[k]; },
};
defineGlobal("localStorage", fakeStorage);
defineGlobal("setTimeout", (fn) => { fn(); return 0; }); // debounced searches run at once
defineGlobal("clearTimeout", () => {});

// ---- fetch stub: routes[ "METHOD path" ] = (init) => [status, body] ----
var routes = {};
var calls = [];
async function fakeFetch(path, init) {
  init = init || {};
  const method = init.method || "GET";
  calls.push({ method, path, headers: init.headers || {}, body: init.body ? JSON.parse(init.body) : undefined });
  const handler = routes[method + " " + path];
  const [status, body] = handler ? handler(init) : [404, { detail: "no stub for " + method + " " + path }];
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => { if (body === undefined) throw new Error("no body"); return JSON.parse(JSON.stringify(body)); },
  };
}

defineGlobal("fetch", fakeFetch);

// Lets pending promise chains run (each await hops one microtask).
async function settle() { for (let i = 0; i < 50; i++) await null; }
function done() { print(`\n${results.pass} passed, ${results.fail} failed`); if (results.fail) quit(1); }
