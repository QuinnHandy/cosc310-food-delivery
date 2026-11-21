# API Contract — Milestones 1 and 2

Version 2 | COSC 310 Food Delivery, Team 11

This contract describes the implemented API as of Milestone 2. It must agree with the FastAPI routes, Pydantic schemas, automated tests, and interactive OpenAPI documentation at [`/docs`](http://127.0.0.1:8000/docs). Update the contract whenever an API endpoint or behavior changes.

## General rules

- **Base URL:** `http://127.0.0.1:8000`
- **Format:** JSON request and response bodies, except operations with no body (including `DELETE` menu-item deactivation, which responds with 204).
- **Authentication:** Protected operations use `Authorization: Bearer <token>`. Obtain a token from `POST /auth/login`. In `/docs`, click **Authorize** and enter the token without the `Bearer` prefix.
- **IDs:** Server-assigned, stable integers. Resource IDs in path parameters refer to existing server records; clients do not supply IDs when creating records.
- **Partial updates:** `PATCH` changes only the fields supplied. Validation and explicit `null` behavior are specific to each request model.
- **Persistence:** Data is stored in JSON files under `data/`, or the directory selected by `APP_DATA_DIR`. `sessions.json` and `carts.json` are runtime-generated and git-ignored; orders are written to `orders.json`.
- **Authorization:** Authentication and role/owner access are checked on the server, not trusted to the browser.

### HTTP status codes and error bodies

| Status | Meaning |
|---|---|
| `200` | Successful read, update, or action |
| `201` | Resource created (restaurant, menu item, customer, or order) |
| `204` | Successful menu-item deactivation; **no response body** |
| `401` | Missing/invalid bearer token or incorrect login credentials |
| `403` | Signed-in user lacks access, or the account is deactivated |
| `404` | Requested restaurant, menu item, customer, cart line, or order does not exist |
| `409` | Conflict, such as duplicate email, unavailable item, mixed-restaurant cart, empty checkout, or an already-deactivated account |
| `422` | Invalid request data, or an application business-rule validation error |
| `500` | Stored application data cannot be accessed |

**Domain errors (implemented by `app/main.py`, #107)** use a consistent response body:

```json
{"detail": "Kung Pao Chicken is not available to order right now", "code": "conflict"}
```

| Domain error | HTTP status | `code` |
|---|---|---|
| `UnauthorizedError` | 401 | `unauthorized` |
| `ForbiddenError` | 403 | `forbidden` |
| `NotFoundError` | 404 | `not_found` |
| `ConflictError` | 409 | `conflict` |
| `BusinessRuleError` | 422 | `business_rule` |
| `DataAccessError` | 500 | `data_access_error` |

For example, a storage failure is returned as `{"detail":"Could not access application data","code":"data_access_error"}`; raw storage exceptions are not exposed. Domain-generated 401 responses include the `WWW-Authenticate: Bearer` header.

**FastAPI/Pydantic validation errors** (such as malformed input, missing required fields, incorrect path types, or invalid schema values) are separate from domain errors and use FastAPI's normal `422` structure with a `detail` array. They do **not** use the `detail`/`code` domain-error object. Endpoint error tables below list relevant status codes; a protected route can also return 500 on storage failure.

### Access shorthand

| Label | Who can call it |
|---|---|
| Public | No token needed |
| Authenticated | Any valid bearer token, subject to session validation |
| Customer | Signed-in, active customer |
| Admin | Signed-in, active administrator |
| Owner/admin | Active restaurant owner or administrator; owner must own the restaurant identified by the path when one is specified |
| Customer/admin | Active customer (own orders only) or active administrator (any order) |

An active customer must be rechecked against stored account state. Owners may change only their restaurant, enforced by `require_restaurant_access` in `app/api/dependencies.py`. For restaurant-specific write operations, a non-admin user without ownership gets 403 even if the restaurant ID does not exist.

## Endpoint summary

`422` may also arise from invalid path/query/body values. `500` applies to data-backed operations, not `/health`; the table shows it explicitly for restaurant listing, where it is the only normal application error.

| Method | Endpoint | Access | Success | Main errors |
|---|---|---|---|---|
| GET | `/health` | Public | 200 | — |
| GET | `/restaurants` | Public | 200 | 500 |
| GET | `/restaurants/{restaurant_id}` | Public | 200 | 404, 422 |
| POST | `/restaurants` | Owner/admin | 201 | 401, 403, 422 |
| PATCH | `/restaurants/{restaurant_id}` | Owner/admin | 200 | 401, 403, 404, 422 |
| GET | `/restaurants/{restaurant_id}/menu` | Public | 200 | 404, 422 |
| POST | `/restaurants/{restaurant_id}/menu` | Owner/admin | 201 | 401, 403, 404, 422 |
| PATCH | `/restaurants/{restaurant_id}/menu/items/{item_id}` | Owner/admin | 200 | 401, 403, 404, 422 |
| DELETE | `/restaurants/{restaurant_id}/menu/items/{item_id}` | Owner/admin | 204 | 401, 403, 404, 422 |
| POST | `/auth/login` | Public | 200 | 401, 403, 422 |
| POST | `/auth/logout` | Authenticated | 200 | 401 |
| POST | `/customers` | Public | 201 | 409, 422 |
| GET | `/customers/me` | Customer | 200 | 401, 403 |
| PATCH | `/customers/me` | Customer | 200 | 401, 403, 422 |
| POST | `/customers/me/deactivate` | Customer | 200 | 401, 403 |
| GET | `/customers/{customer_id}` | Admin | 200 | 401, 403, 404, 422 |
| POST | `/customers/{customer_id}/deactivate` | Admin | 200 | 401, 403, 404, 409, 422 |
| GET | `/cart` | Customer | 200 | 401, 403 |
| POST | `/cart/items` | Customer | 200 | 401, 403, 404, 409, 422 |
| PATCH | `/cart/items/{menu_item_id}` | Customer | 200 | 401, 403, 404, 422 |
| DELETE | `/cart/items/{menu_item_id}` | Customer | 200 | 401, 403, 404, 422 |
| DELETE | `/cart/items` | Customer | 200 | 401, 403 |
| POST | `/checkout` | Customer | 201 | 401, 403, 409, 422 |
| GET | `/customers/me/orders` | Customer | 200 | 401, 403 |
| GET | `/customers/{customer_id}/orders` | Admin | 200 | 401, 403, 404, 422 |
| GET | `/orders/{order_id}` | Customer/admin | 200 | 401, 403, 404, 422 |

**Not implemented:** `GET /restaurants/{restaurant_id}/menu/items` and `POST /restaurants/{restaurant_id}/menu/items` are obsolete paths from the M1 draft. The actual menu read and create paths are `/restaurants/{restaurant_id}/menu`, with GET and POST respectively.

## API models

### Restaurant models

`Restaurant`: `id: int` (server-assigned), `name: str`, `cuisine: str`.

`RestaurantCreate`: required non-empty `name` and `cuisine`. The server assigns `id`.

`RestaurantUpdate`: optional `name` and `cuisine`, each required to be non-empty when provided as a new string. Unspecified fields remain unchanged.

```json
{"id":1,"name":"Golden Dragon","cuisine":"Chinese"}
```

The older M1 draft listed address, delivery estimates, ratings, restaurant-specific fees, and other restaurant fields. **Those are not fields in the current `Restaurant` Pydantic model and are not part of this API contract.** The flat cart/checkout delivery fee is configured separately.

### Menu models

`MenuItemCreate` (request): required `name: str` (non-empty), `price: float` (greater than zero), and `category: str` (non-empty); optional `description: str = ""`, `is_available: bool = true`, and `image_url: str = ""`.

`MenuItemUpdate` (PATCH request): any of `name`, `description`, `price`, `is_available`, `category`, `image_url`. Fields omitted from the request are left unchanged. **Explicit `null` values are rejected with 422**, even for an otherwise-valid partial update (#130).

`MenuItem` / `MenuItemResponse`: the menu-item fields above, plus `id: int`, `restaurant_id: int`, and `is_active: bool` (defaults to true). `is_available: false` temporarily prevents ordering. `is_active: false` represents a permanent soft-deactivation via DELETE; PATCH does not set `is_active`.

`MenuResponse` (GET): `restaurant_id: int` and `items: list[MenuItemResponse]` sorted by item ID. The response does **not** include `restaurant_name` or a nested `categories` array.

```json
{
  "restaurant_id": 1,
  "items": [
    {
      "id": 1,
      "restaurant_id": 1,
      "name": "Kung Pao Chicken",
      "description": "Peanuts, chili, and diced chicken",
      "price": 15.5,
      "is_available": true,
      "category": "Mains",
      "image_url": "",
      "is_active": true
    }
  ]
}
```

### Authentication and customer models

- `LoginRequest`: `email: str`, `password: str` (non-empty).
- `LoginResponse`: `token: str`, `user_id: int`, `role` (`customer`, `restaurant_owner`, or `admin`).
- `MessageResponse`: `message: str`.
- `CustomerCreate`: required `name: str` (non-blank), `email: str` (valid, unique), `password: str` (at least 8 characters). Optional `phone` and `delivery_address` default to empty strings. Unknown fields, including `role`, are rejected with 422; new accounts are always customers.
- `CustomerUpdate`: optional `name`, `phone`, `delivery_address`. Omitted fields and fields explicitly set to `null` remain unchanged. `name` and `delivery_address` cannot be blank if set; `phone` may be empty. Other fields (`email`, `role`, `is_active`, `id`, etc.) are rejected with 422.
- `CustomerResponse`: `id`, `email`, `name`, `phone`, `delivery_address`, `is_active`. Passwords and password hashes are **never** returned.

```json
{
  "id": 4,
  "email": "alice@foodapp.test",
  "name": "Alice Smith",
  "phone": "250-555-0101",
  "delivery_address": "123 Main St, Kelowna, BC",
  "is_active": true
}
```

### Cart models

- `CartItemAdd`: `menu_item_id: int` (required) and `quantity: int` (default 1, range 1–20). Both fields use strict integers; strings, booleans, and fractional numbers are not accepted as integers.
- `CartItemUpdate`: `quantity: int`, required strict integer from 1 to 20.
- `CartResponse`: `id`, `customer_id`, `restaurant_id` (nullable for an empty cart), `status` (`active` or `checked_out`), `items: list[CartLineResponse]`, `subtotal`, `delivery_fee`, and `total`.
- `CartLineResponse`: `menu_item_id`, current `name`, current `unit_price`, `quantity`, calculated `line_total`, and `is_available`.

```json
{
  "id": 1,
  "customer_id": 4,
  "restaurant_id": 1,
  "status": "active",
  "items": [
    {"menu_item_id":1,"name":"Kung Pao Chicken","unit_price":15.5,"quantity":2,"line_total":31.0,"is_available":true}
  ],
  "subtotal": 31.0,
  "delivery_fee": 4.99,
  "total": 35.99
}
```

The stored cart contains **only** item IDs and quantities. Prices, availability, totals, and the flat $4.99 delivery fee are calculated by the backend. An empty cart has a delivery fee of $0.00. One cart can contain items from **one restaurant only**.

### Order models

`Order` / checkout response: `id: int`, `customer_id: int`, `restaurant_id: int`, `restaurant_name: str`, `delivery_address: str`, `items: list[OrderLine]`, `subtotal: float`, `delivery_fee: float`, `total: float`, `status: "placed"`, `created_at: datetime` (UTC).

Each `OrderLine` has `menu_item_id: int`, `name: str`, `unit_price: float`, `quantity: int`, and `line_total: float`. Prices and names are snapshots from **the time of checkout**, not live menu values.

```json
{
  "id": 1,
  "customer_id": 4,
  "restaurant_id": 1,
  "restaurant_name": "Golden Dragon",
  "delivery_address": "123 Main St, Kelowna, BC",
  "items": [
    {"menu_item_id":1,"name":"Kung Pao Chicken","unit_price":15.5,"quantity":2,"line_total":31.0}
  ],
  "subtotal": 31.0,
  "delivery_fee": 4.99,
  "total": 35.99,
  "status": "placed",
  "created_at": "2026-11-20T09:00:00Z"
}
```

## Endpoint details

### Health and restaurants

#### `GET /health`

- **Access:** Public. **Request:** No body or parameters.
- **Response 200:** `HealthResponse`, `{"status":"ok"}`.
- **Errors:** No application error responses documented.

#### `GET /restaurants`

- **Access:** Public. **Request:** No body.
- **Query parameters:** `name` (optional partial, case-insensitive restaurant-name match); `cuisine` (optional exact, case-insensitive cuisine match). Leading/trailing whitespace is stripped; blank filters are ignored; both filters combine with AND.
- **Response 200:** `list[Restaurant]` sorted by ID; `[]` when no restaurants match.
- **Errors:** 500 on data access failure.
- **Example:** `/restaurants?name=dragon&cuisine=chinese`.

#### `GET /restaurants/{restaurant_id}`

- **Access:** Public. **Request:** Path `restaurant_id: int`; no body.
- **Response 200:** `Restaurant`.
- **Errors:** 404 if unknown restaurant; 422 for non-integer path ID; 500 for storage errors.

#### `POST /restaurants`

- **Access:** Owner/admin. **Request:** `RestaurantCreate` JSON, for example `{"name":"Pasta Place","cuisine":"Italian"}`.
- **Response 201:** Created `Restaurant` with server-generated `id`.
- **Errors:** 401 unauthenticated, 403 wrong role/deactivated, 422 invalid or missing fields, 500 storage error.

#### `PATCH /restaurants/{restaurant_id}`

- **Access:** Admin or owner of that restaurant. **Request:** Integer path ID and `RestaurantUpdate`, for example `{"name":"New Name"}`.
- **Response 200:** Updated `Restaurant`.
- **Errors:** 401 no token, 403 wrong owner/role/deactivated, 404 unknown restaurant, 422 invalid request, 500 storage error. Unauthorized owners get 403 even for nonexistent IDs.

### Menu management

#### `GET /restaurants/{restaurant_id}/menu`

- **Access:** Public. **Request:** Integer `restaurant_id`, no body.
- **Response 200:** `MenuResponse` with flat `items` array sorted by ID. The array is empty when the restaurant has no visible items. Unavailable items (`is_available: false`) are visible, but deactivated items (`is_active: false`) are hidden.
- **Errors:** 404 unknown restaurant, 422 non-integer path ID, 500 storage error.

#### `POST /restaurants/{restaurant_id}/menu`

- **Access:** Admin or owner of that restaurant. **Request:** Integer `restaurant_id`, `MenuItemCreate` JSON.

```json
{"name":"Garlic Knots","description":"Six knots with marinara","price":7.5,"is_available":true,"category":"Starters","image_url":""}
```

- **Response 201:** Created `MenuItem`, including server-assigned `id` and `restaurant_id`.
- **Errors:** 401 missing/invalid session, 403 wrong owner/role/deactivated, 404 unknown restaurant, 422 missing or invalid fields, 500 storage error.

#### `PATCH /restaurants/{restaurant_id}/menu/items/{item_id}`

- **Access:** Admin or owner of that restaurant. **Request:** Integer `restaurant_id` and `item_id`; `MenuItemUpdate` JSON, for example `{"price":8.25,"is_available":false,"category":"Sides"}`.
- **Response 200:** Updated `MenuItem`.
- **Errors:** 401 missing token, 403 wrong owner/role/deactivated, 404 restaurant/item missing or item belongs elsewhere, 422 invalid value or **explicit null** (for example `{"price":null}`), 500 storage error.
- **Rules:** Setting `is_available: false` temporarily makes an item unorderable without hiding it from the public menu. Setting it back to `true` restores orderability if the item remains active. `is_active` is not a PATCH field; use DELETE to deactivate.

#### `DELETE /restaurants/{restaurant_id}/menu/items/{item_id}`

- **Access:** Admin or owner of that restaurant. **Request:** Integer `restaurant_id` and `item_id`; no body.
- **Response 204:** No response body. Soft-deactivates the item, retaining it in `menus.json` so historical references remain valid. Repeated deactivation also returns 204.
- **Errors:** 401 missing token, 403 wrong owner/role/deactivated, 404 restaurant/item missing or item belongs elsewhere, 422 invalid ID, 500 storage error.
- **Rules:** A deactivated item disappears from the public menu, cannot be added to carts, and causes checkout to refuse an existing cart containing it.

### Authentication

#### `POST /auth/login`

- **Access:** Public. **Request:** `LoginRequest` JSON, for example `{"email":"alice@foodapp.test","password":"Password123!"}`.
- **Response 200:** `LoginResponse` with `token`, `user_id`, `role`.

```json
{"token":"<generated-session-token>","user_id":4,"role":"customer"}
```

- **Errors:** 401 incorrect email/password (identical message, `unauthorized`), 403 valid credentials for a deactivated account (`forbidden`), 422 malformed or missing request fields, 500 storage error.
- **Rules:** Emails are matched case-insensitively. A successful login creates a session in `data/sessions.json`.

#### `POST /auth/logout`

- **Access:** Authenticated bearer token. **Request:** No body; header `Authorization: Bearer <token>`.
- **Response 200:** `MessageResponse`, `{"message":"Signed out"}`.
- **Errors:** 401 absent/unknown/already-revoked token, 500 storage error.
- **Rules:** Removes that session; subsequent uses of the token return 401. The route only checks bearer credentials and session deletion rather than requiring a particular role.

### Customers

#### `POST /customers`

- **Access:** Public. **Request:** `CustomerCreate`, e.g. `{"name":"Dana Park","email":"dana@example.com","password":"longenough","delivery_address":"1 Lake Rd"}`.
- **Response 201:** `CustomerResponse`, with no password or hash.
- **Errors:** 409 duplicate email (`code: conflict`), 422 invalid email, short password, blank name, or unknown fields; 500 storage error.
- **Rules:** Email is stored lowercase; new account role is always `customer`.

#### `GET /customers/me`

- **Access:** Customer. **Request:** No body; customer inferred from token.
- **Response 200:** `CustomerResponse`.
- **Errors:** 401 missing token, 403 wrong role/deactivated, 500 storage error.

#### `PATCH /customers/me`

- **Access:** Customer. **Request:** `CustomerUpdate`, e.g. `{"name":"Alice S.","delivery_address":"45 Lake Rd"}`.
- **Response 200:** Updated `CustomerResponse`.
- **Errors:** 401 missing token, 403 wrong role/deactivated, 422 invalid fields or unknown fields, 500 storage error.
- **Rules:** Only `name`, `phone`, and `delivery_address` can be changed. Omitted or null-valued fields are ignored. Cannot update email, role, account status, or ID here.

#### `POST /customers/me/deactivate`

- **Access:** Customer. **Request:** No body.
- **Response 200:** `CustomerResponse` with `is_active: false`.
- **Errors:** 401 missing token, 403 wrong role/already-deactivated session, 500 storage error.
- **Rules:** Record is retained. Existing sessions stop working on protected endpoints because authentication rechecks account state.

#### `GET /customers/{customer_id}`

- **Access:** Admin. **Request:** Integer `customer_id`, no body.
- **Response 200:** `CustomerResponse`.
- **Errors:** 401 missing token, 403 non-admin/deactivated, 404 unknown ID or ID belonging to a non-customer, 422 invalid path ID, 500 storage error.

#### `POST /customers/{customer_id}/deactivate`

- **Access:** Admin. **Request:** Integer `customer_id`; no body.
- **Response 200:** `CustomerResponse` with `is_active: false`.
- **Errors:** 401 missing token, 403 non-admin/deactivated, 404 unknown customer, 409 already deactivated (`code: conflict`), 422 invalid ID, 500 storage error.

### Shopping cart

All cart endpoints require an active customer. A customer has at most one active cart; `GET /cart` creates an empty one on first use. The cart does not store prices. Totals are recomputed using current menu prices and the shared pricing function in `app/services/pricing.py`.

#### `GET /cart`

- **Access:** Customer. **Request:** No body.
- **Response 200:** `CartResponse`. Creates an empty active cart if one does not exist; returns the existing active cart otherwise.
- **Errors:** 401 missing token, 403 wrong role/deactivated, 500 storage error.

#### `POST /cart/items`

- **Access:** Customer. **Request:** `CartItemAdd` JSON, for example `{"menu_item_id":1,"quantity":2}`. Quantity defaults to one.
- **Response 200:** Updated `CartResponse`. Re-adding an item increases the quantity.
- **Errors:** 401 missing token, 403 wrong role/deactivated, 404 unknown item, 409 item unavailable/deactivated or from another restaurant, 422 invalid quantity or quantity exceeding 20 after addition, 500 storage error.
- **Rules:** First item chooses the cart's restaurant. Adding from a different restaurant is rejected without changing the stored cart. Quantity must stay between 1 and 20 per item.

#### `PATCH /cart/items/{menu_item_id}`

- **Access:** Customer. **Request:** Integer `menu_item_id`; `CartItemUpdate` JSON, for example `{"quantity":3}`.
- **Response 200:** Updated `CartResponse`.
- **Errors:** 401 missing token, 403 wrong role/deactivated, 404 item not currently in cart, 422 invalid quantity or path ID, 500 storage error.

#### `DELETE /cart/items/{menu_item_id}`

- **Access:** Customer. **Request:** Integer `menu_item_id`; no body.
- **Response 200:** Updated `CartResponse`, with the line removed.
- **Errors:** 401 missing token, 403 wrong role/deactivated, 404 item not in cart, 422 invalid ID, 500 storage error.
- **Rules:** Removing the last item resets `restaurant_id` to null.

#### `DELETE /cart/items`

- **Access:** Customer. **Request:** No body.
- **Response 200:** Updated empty `CartResponse`; retains the active cart ID but resets its restaurant.
- **Errors:** 401 missing token, 403 wrong role/deactivated, 500 storage error.

### Checkout

#### `POST /checkout`

- **Access:** Customer. **Request:** **No body**. Cart contents, delivery address, prices, and fee are taken from the server.
- **Response 201:** `Order`, with server-assigned ID, UTC creation time, `status: "placed"`, item snapshots, and totals.
- **Errors:** 401 missing token, 403 wrong role/deactivated, 409 empty cart, missing/disabled/removed menu item, or missing restaurant; 422 no delivery address or invalid stored quantity; 500 storage error.
- **Rules:** Checkout rechecks current customer status, restaurant, each item, and quantity before saving. It prices items from the **current** menu, even if the owner changed a price after the item was added to the cart. A disabled or deactivated item returns 409 and the order is not written. The order is saved before the cart is marked `checked_out`; if saving fails, the active cart remains unchanged. After successful checkout, the next `GET /cart` creates a new empty active cart.

**Example conflict:**

```json
{"detail":"Vegetable Spring Rolls is not available to order right now","code":"conflict"}
```

**Example business-rule failure:**

```json
{"detail":"Add a delivery address to your profile before checking out","code":"business_rule"}
```

### Orders and order history

Read operations do not mutate stored orders. Order lists are returned newest first. Placed orders preserve the restaurant name, menu-item names, prices, quantities, delivery address, and totals from checkout even if the menu is edited later.

#### `GET /customers/me/orders`

- **Access:** Customer. **Request:** No body; customer from token.
- **Response 200:** `list[Order]` belonging to the signed-in customer, newest first. Returns `[]` if there are no orders.
- **Errors:** 401 missing token, 403 wrong role/deactivated, 500 storage error.

#### `GET /customers/{customer_id}/orders`

- **Access:** Admin. **Request:** Integer `customer_id`; no body.
- **Response 200:** `list[Order]` for that customer, newest first, or `[]` if none; deactivated customers' historical orders remain readable by an admin.
- **Errors:** 401 missing token, 403 non-admin/deactivated, 404 customer not found or ID belongs to a non-customer, 422 invalid ID, 500 storage error.

#### `GET /orders/{order_id}`

- **Access:** Customer/admin. **Request:** Integer `order_id`; no body.
- **Response 200:** A single `Order` snapshot.
- **Errors:** 401 missing token, 403 restaurant owner/deactivated account/customer asking for another customer's order, 404 order not found, 422 invalid ID, 500 storage error.
- **Rules:** Customers can retrieve only their own orders. Admins can retrieve any order, including those of deactivated customers. An existing order never reprices when a menu item is edited.

## Where rules are implemented

| Concern | Implementation |
|---|---|
| Authentication and token lookup | `app/services/auth_service.py`; `get_bearer_token` and `get_current_user` in `app/api/dependencies.py` |
| Role and restaurant-owner authorization | `require_role` and `require_restaurant_access` in `app/api/dependencies.py` |
| Customer eligibility | `CustomerService.require_active_customer` in `app/services/customer_service.py` |
| Menu-item orderability | `MenuService.is_orderable` and `get_orderable_item` in `app/services/menu_service.py` |
| Cart validation | `app/services/cart_service.py` |
| Checkout revalidation and order placement | `app/services/checkout_service.py` |
| Money calculation | `app/services/pricing.py`, using `Decimal` |
| Order listing/ownership | `app/services/order_service.py` |
| Domain exception-to-HTTP mapping | `app/core/errors.py` and `app/main.py` |
| JSON persistence | `app/repositories/` |

## OpenAPI and testing

- **Interactive OpenAPI:** `/docs`; raw schema at `/openapi.json`.
- `tests/test_openapi.py` verifies the documented endpoint set, descriptions, parameter documentation, success schemas, security declarations, and important error response schemas. Issue #110 extends this coverage across M2 routes.
- Integration tests validate owner changes to prices and availability at checkout (#103), shared business rules (#109), and the standardized domain error mapping (#107).
- Run all tests with `python -m pytest -q`. Tests that write data use temporary locations; they should not modify committed sample files.

The HTML pages (`/`, `/owner`, `/account`, `/orders`) are front-end routes rather than JSON API operations and are intentionally absent from the OpenAPI endpoint list.
