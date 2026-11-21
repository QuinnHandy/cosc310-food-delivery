# COSC 310 Food Delivery

**Team 11** — A food delivery application built with FastAPI, Pydantic, a small web frontend, and JSON-file persistence.

## Milestone 2 — Integrated Food Delivery System

Milestone 2 extends the Milestone 1 restaurant browsing and management features into a connected ordering workflow:

- **Authentication:** Sign in and out with bearer-token sessions.
- **Customer accounts:** Register, view or update a profile and delivery address, and deactivate an account.
- **Restaurant and menu management:** Authorized owners and administrators can create and update restaurants, add and edit menu items, change availability, and deactivate items.
- **Shopping cart:** Customers can add, update, remove, and clear items. Cart prices reflect the current menu.
- **Checkout:** Customers can place an order from their cart. The server rechecks customer eligibility, delivery address, item availability, quantities, and current prices.
- **Order history:** Customers can view their own orders; administrators can view customers' orders. Orders retain the item names and prices recorded at checkout.
- **Consistent errors:** Expected application errors are translated into HTTP responses by a central handler, with a human-readable `detail` and a machine-readable `code`.

## Requirements

- Python 3.13 or newer
- Git

## Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/QuinnHandy/cosc310-food-delivery.git
   cd cosc310-food-delivery
   ```

2. Create and activate a virtual environment:

   **macOS / Linux**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

   **Windows (PowerShell)**

   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. Install the dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

## Running the Application

With the virtual environment activated, start the server:

```bash
uvicorn app.main:app --reload
```

The application is available at `http://127.0.0.1:8000`.

| URL | Purpose |
|---|---|
| [`/`](http://127.0.0.1:8000/) | Customer page: browse/search restaurants, view menus, and use the cart |
| [`/account`](http://127.0.0.1:8000/account) | Sign in, register, and manage a customer profile and delivery address |
| [`/orders`](http://127.0.0.1:8000/orders) | View a customer's order history |
| [`/owner`](http://127.0.0.1:8000/owner) | Restaurant management page (requires an owner or administrator account for changes) |
| [`/docs`](http://127.0.0.1:8000/docs) | Interactive Swagger/OpenAPI documentation and API testing |
| [`/openapi.json`](http://127.0.0.1:8000/openapi.json) | Generated OpenAPI specification |

The frontend includes sign-in and sign-out controls. Access permissions are checked by the backend, not by the web pages.

## Demo Accounts and Authentication

The seeded users in `data/users.json` share the **demo-only** password `Password123!`.

| Email | Role | Notes |
|---|---|---|
| `admin@foodapp.test` | `admin` | May manage restaurants and view customer accounts and orders |
| `owner1@foodapp.test` | `restaurant_owner` | Owns Golden Dragon (restaurant 1) |
| `owner2@foodapp.test` | `restaurant_owner` | Owns Spice Garden (restaurant 2) |
| `alice@foodapp.test` | `customer` | Active customer with a delivery address |
| `bob@foodapp.test` | `customer` | Active customer with a delivery address |
| `carol@foodapp.test` | `customer` | Deactivated account; useful for testing rejected access |

You can sign in through the `/account` page or use the API:

1. Open `/docs` and expand **POST `/auth/login`**.
2. Select **Try it out** and enter an email and the demo password.
3. Execute the request and copy the returned `token`.
4. Select **Authorize** at the top of `/docs` and paste the token **without** `Bearer`.
5. Swagger UI then sends the `Authorization: Bearer <token>` header for protected requests.

Example request:

```json
{"email": "alice@foodapp.test", "password": "Password123!"}
```

Successful sign-in returns a JSON object containing `token`, `user_id`, and `role`. `POST /auth/logout` invalidates that token. Sessions are stored in `data/sessions.json`, so they persist across server restarts unless invalidated. A deactivated account cannot sign in or use an existing token for protected endpoints.

## API Endpoints

The application has **26 API operations**. For full request models, response bodies, parameter descriptions, and status codes, see [the API contract](docs/api-contract.md) and the live [`/docs`](http://127.0.0.1:8000/docs) page.

**Access key:** Public = no token required; Customer = signed-in active customer; Owner/admin = a restaurant owner with permission for that restaurant, or an administrator; Admin = administrator only.

### Health, Restaurants, and Menus

| Method | Path | Access | Success | Purpose |
|---|---|---|---|---|
| GET | `/health` | Public | 200 | Health check (`{"status":"ok"}`) |
| GET | `/restaurants` | Public | 200 | List/search restaurants; optional `name` and `cuisine` filters |
| GET | `/restaurants/{restaurant_id}` | Public | 200 | View restaurant details |
| POST | `/restaurants` | Owner or admin | 201 | Create a restaurant |
| PATCH | `/restaurants/{restaurant_id}` | Owner/admin | 200 | Update a restaurant's name or cuisine |
| GET | `/restaurants/{restaurant_id}/menu` | Public | 200 | View active menu items, including items marked unavailable |
| POST | `/restaurants/{restaurant_id}/menu` | Owner/admin | 201 | Add a menu item |
| PATCH | `/restaurants/{restaurant_id}/menu/items/{item_id}` | Owner/admin | 200 | Edit an item's details, price, or availability |
| DELETE | `/restaurants/{restaurant_id}/menu/items/{item_id}` | Owner/admin | 204 | Deactivate a menu item (soft delete) |

Restaurant search examples: `/restaurants?name=piz`, `/restaurants?cuisine=italian`, and `/restaurants?name=piz&cuisine=italian`. Name matching is partial and case-insensitive; cuisine matching is exact and case-insensitive. Filters are combined when both are supplied.

**Note:** An owner can modify only their assigned restaurant. `POST /restaurants` accepts either a restaurant-owner or administrator token.

### Authentication and Customers

| Method | Path | Access | Success | Purpose |
|---|---|---|---|---|
| POST | `/auth/login` | Public | 200 | Sign in and receive a bearer token |
| POST | `/auth/logout` | Valid bearer token | 200 | Sign out and invalidate the token |
| POST | `/customers` | Public | 201 | Register a new customer |
| GET | `/customers/me` | Customer | 200 | View own profile |
| PATCH | `/customers/me` | Customer | 200 | Update name, phone, or delivery address |
| POST | `/customers/me/deactivate` | Customer | 200 | Deactivate own account |
| GET | `/customers/{customer_id}` | Admin | 200 | View a customer's profile |
| POST | `/customers/{customer_id}/deactivate` | Admin | 200 | Deactivate a customer |

Registration requires a name, unique email, and password of at least eight characters. A customer can change `name`, `phone`, and `delivery_address` through `PATCH /customers/me`; other profile fields cannot be changed through that endpoint.

### Cart and Checkout

| Method | Path | Access | Success | Purpose |
|---|---|---|---|---|
| GET | `/cart` | Customer | 200 | Get or create the active cart |
| POST | `/cart/items` | Customer | 200 | Add a menu item, or increase its quantity |
| PATCH | `/cart/items/{menu_item_id}` | Customer | 200 | Set a cart item's quantity |
| DELETE | `/cart/items/{menu_item_id}` | Customer | 200 | Remove a cart item |
| DELETE | `/cart/items` | Customer | 200 | Clear the cart |
| POST | `/checkout` | Customer | 201 | Validate the cart and place an order |

Example: add two units of menu item 1 to your cart using `POST /cart/items`:

```json
{"menu_item_id": 1, "quantity": 2}
```

Checkout takes **no request body**: the server uses the signed-in customer, saved cart, saved delivery address, and current menu prices.

### Orders

| Method | Path | Access | Success | Purpose |
|---|---|---|---|---|
| GET | `/customers/me/orders` | Customer | 200 | View own orders, newest first |
| GET | `/customers/{customer_id}/orders` | Admin | 200 | View a customer's orders, newest first |
| GET | `/orders/{order_id}` | Customer (own order) or admin | 200 | View one order and its checkout-time snapshot |

An account without orders receives `200` and an empty list (`[]`) when listing its orders. Customers cannot view other customers' orders.

## Business Rules and Where They Are Enforced

- **HTTP requests and permissions:** `app/api/routes/` defines the routes. `app/api/dependencies.py` authenticates bearer tokens through `get_current_user` and enforces roles using `require_role` and `require_restaurant_access`.
- **Customer eligibility:** `CustomerService.require_active_customer` in `app/services/customer_service.py` checks that the current account is an active customer, including when an account was deactivated after a session was created.
- **Menu eligibility:** `MenuService.get_orderable_item` in `app/services/menu_service.py` checks that an item still exists, is active, and is available. Both cart and checkout use the shared menu rules.
- **Cart rules:** `app/services/cart_service.py` allows items from only one restaurant per cart and quantities of 1–20 per item. The stored cart contains item IDs and quantities, not fixed prices.
- **Pricing:** `app/services/pricing.py` calculates line totals, subtotals, and the delivery fee using `Decimal`. The default fee is **$4.99** for a nonempty cart, configured in `app/core/config.py`.
- **Checkout:** `app/services/checkout_service.py` requires a delivery address, rechecks every item's availability and current price, and creates the order only after validation passes. Unavailable or deactivated items prevent checkout; the cart is preserved when validation fails.
- **Orders:** Placed orders store item names, quantities, prices, delivery address, and totals as a historical snapshot. Later restaurant or menu edits do not change them.
- **Persistence:** `app/repositories/` loads and saves the JSON records. Services use repositories rather than accessing JSON files directly.

### Error Handling

The central handler in `app/main.py` converts expected `DomainError` subclasses from `app/core/errors.py` into consistent responses, for example:

```json
{"detail": "Kung Pao Chicken is not available to order right now", "code": "conflict"}
```

| Status | `code` | Meaning |
|---|---|---|
| 401 | `unauthorized` | Missing/invalid authentication or incorrect sign-in credentials |
| 403 | `forbidden` | Deactivated account or insufficient permission |
| 404 | `not_found` | Requested restaurant, menu item, customer, order, or cart item not found |
| 409 | `conflict` | Conflicting state, such as unavailable items or an empty cart at checkout |
| 422 | `business_rule` | Domain/business-rule violation, such as a missing delivery address |
| 500 | `data_access_error` | Storage error; internal details are not exposed |

**Validation exception:** FastAPI/Pydantic request validation errors also use HTTP **422**, but may return the framework's standard `detail` array instead of a domain-error `code`. Responses with status 401 include the `WWW-Authenticate: Bearer` header.

## Data Storage

By default, the application stores data in the `data/` directory.

| File | Contents |
|---|---|
| `data/restaurants.json` | Restaurants |
| `data/menus.json` | Menu items, current prices, availability, and activation state |
| `data/users.json` | Accounts, roles, customer details, and password hashes |
| `data/sessions.json` | Bearer-token sessions (created at runtime; Git-ignored) |
| `data/carts.json` | Customer carts (created at runtime; Git-ignored) |
| `data/orders.json` | Orders and their checkout-time snapshots |

- Passwords are saved as salted PBKDF2-SHA256 hashes, not plaintext.
- Saved changes can survive restarting the server. JSON repositories use temporary-file replacement for writes to avoid partially written files.
- Record IDs are server-assigned and stable.
- Set `APP_DATA_DIR` before starting the app to use a different data directory. For example, on macOS/Linux: `APP_DATA_DIR=/path/to/data uvicorn app.main:app --reload`.
- API operations can change files under `data/`. To discard **uncommitted modifications to tracked sample files**, use `git restore -- data/`. This is destructive to local tracked changes and does not remove runtime-generated, Git-ignored files.

## Running Tests

The dependencies in `requirements.txt` include pytest and the HTTP test client tools.

Run the full suite:

```bash
python -m pytest -q
```

Run one test file:

```bash
python -m pytest tests/test_openapi.py -v
```

Check the patch for whitespace errors before committing:

```bash
git diff --check
```

Tests exercise the API, services, repositories, permissions, validation, pricing, checkout, order history, and multi-subsystem workflows. Data-writing tests use temporary files and test fixtures (including `tests/app_data_helpers.py`) so they do not alter the committed seed data. `tests/test_openapi.py` checks the documented API operations and OpenAPI response/parameter metadata.

## Repository Structure

```text
app/
  api/routes/       # HTTP endpoints
  api/dependencies.py
  core/             # Configuration, domain errors, and security helpers
  repositories/     # JSON-file data access
  schemas/          # Request and response models
  services/         # Authentication and business rules
  static/           # Web frontend
  main.py           # FastAPI application and centralized error handler
data/               # Seed and runtime JSON data
docs/               # API contract, decision receipts, provenance
scrum/              # Team agreement and sprint notes
tests/              # Unit, API, OpenAPI, and integration tests
.github/workflows/  # GitHub Actions CI
```

## Continuous Integration

GitHub Actions runs the Python test suite on pushes and pull requests using Python 3.13 and the dependencies in `requirements.txt`. See [`.github/workflows/tests.yml`](.github/workflows/tests.yml). PRs should pass CI and receive a teammate review before merging.

## Project Documentation

- [API contract](docs/api-contract.md) — Request/response models and status codes for Milestones 1 and 2.
- [Decision receipt](docs/decision-receipt.md) — Engineering decisions and milestone evidence.
- [Provenance](docs/PROVENANCE.md) — Record of externally assisted work.
- [Sprint documents](scrum/) — Team process and sprint notes.
