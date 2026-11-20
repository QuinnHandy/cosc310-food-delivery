# M1 API Contract

Version 1 | Milestone 1 (Restaurant vertical slice)

This document defines every M1 endpoint. The implementation, the tests, and the OpenAPI docs at `/docs` must match it. If an endpoint changes, update this file in the same PR.

## General Rules

- **Base URL:** `http://127.0.0.1:8000`
- **Format:** all request and response bodies are JSON.
- **IDs:** assigned by the server, never sent by the client, and never changed.
- **Updates:** `PATCH` with partial bodies. Only the fields sent are changed.
- **Errors:** use FastAPI's format: `{"detail": "<message>"}`

| Status | Meaning |
|---|---|
| 200 | Success |
| 201 | Resource created |
| 401 | Wrong email or password, or a missing or invalid bearer token |
| 403 | The account has been deactivated, or the signed-in user is not allowed (wrong role, or not the owner of this restaurant) |
| 404 | Restaurant or menu item not found |
| 422 | Invalid request (missing field, wrong type, failed validation) |
| 500 | Stored data could not be read |

## Models

### Restaurant
| Field | Type | Rules |
|---|---|---|
| id | int | Server-assigned, stable |
| name | str | Required, not empty |
| cuisine | str | Required, not empty |
| description | str | Optional, defaults to "" |
| address | str | Required, not empty |
| image_url | str | Optional, defaults to "" |
| rating | float | 0.0-5.0, server-managed (defaults to 0.0) |
| review_count | int | >= 0, server-managed (defaults to 0) |
| delivery_time_min | int | Required, minutes, >= 0 |
| delivery_time_max | int | Required, minutes, >= delivery_time_min |
| delivery_fee | float | Required, >= 0 |
| min_order | float | Required, >= 0 |

- **RestaurantCreate:** all fields except `id`, `rating`, and `review_count`
- **RestaurantUpdate:** all RestaurantCreate fields, each optional

### MenuItem
| Field | Type | Rules |
|---|---|---|
| id | int | Server-assigned, stable |
| restaurant_id | int | The restaurant this item belongs to |
| name | str | Required, not empty |
| description | str | Optional, defaults to "" |
| price | float | Required, greater than 0 |
| is_available | bool | Defaults to true |
| category | str | Required, e.g. "Pizza", "Starters" |
| image_url | str | Optional, defaults to "" |

- **MenuItemCreate:** `name`, `description`, `price`, `is_available`, `category`, `image_url`. `id` and `restaurant_id` are set by the server.
- **MenuItemUpdate:** all MenuItemCreate fields, each optional

### Menu
| Field | Type |
|---|---|
| restaurant_id | int |
| restaurant_name | str |
| categories | list[MenuCategory] |

### MenuCategory
| Field | Type |
|---|---|
| name | str |
| items | list[MenuItem] |

## Endpoint Summary

| # | Method | Path | Purpose | Success | Errors |
|---|---|---|---|---|---|
| 1 | GET | `/restaurants` | List restaurants, with optional search/filter | 200 | 422 |
| 2 | GET | `/restaurants/{restaurant_id}` | Restaurant details | 200 | 404, 422 |
| 3 | POST | `/restaurants` | Create a restaurant (owner or admin) | 201 | 401, 403, 422 |
| 4 | PATCH | `/restaurants/{restaurant_id}` | Update a restaurant (its owner or admin) | 200 | 401, 403, 404, 422 |
| 5 | GET | `/restaurants/{restaurant_id}/menu` | View a restaurant's menu | 200 | 404, 422 |
| 6 | GET | `/restaurants/{restaurant_id}/menu/items` | List menu items | 200 | 404, 422 |
| 7 | POST | `/restaurants/{restaurant_id}/menu/items` | Add a menu item (the restaurant's owner or admin) | 201 | 401, 403, 404, 422 |
| 8 | PATCH | `/restaurants/{restaurant_id}/menu/items/{item_id}` | Update a menu item, including `is_available` (the restaurant's owner or admin) | 200 | 401, 403, 404, 422 |
| 9 | DELETE | `/restaurants/{restaurant_id}/menu/items/{item_id}` | Deactivate a menu item, a soft delete (the restaurant's owner or admin) | 204 | 401, 403, 404 |

Every endpoint can also return 500 if the stored data can't be read. The `GET` endpoints are public and need no token. For who may call the others, see [Protected endpoints](#protected-endpoints).

## Endpoints

### 1. List, search, and filter restaurants
`GET /restaurants`

Returns all restaurants sorted by `id`. Optional query parameters narrow the results. Filters combine with AND.

**Query parameters**
- `name` (str, optional): partial match on restaurant name, ignoring case, e.g. `?name=piz` finds "Pizza Place".
- `cuisine` (str, optional): exact match on cuisine, ignoring case, e.g. `?cuisine=italian`. A partial value like `?cuisine=ital` matches nothing.

Spaces at either end of a value are trimmed. An empty or spaces-only parameter is ignored, so `?name=` returns every restaurant. If both parameters are given, a restaurant must match both.

**Response 200:** `list[Restaurant]`, sorted by `id`. If nothing matches, the response is `200` with an empty list `[]`, not a `404`.
```json
[{
  "id": 1,
  "name": "Mama Rosa's Pizza",
  "cuisine": "Italian",
  "description": "Authentic Neapolitan pizza and homemade pasta.",
  "address": "901 Columbus Ave, San Francisco, CA 94133",
  "image_url": "",
  "rating": 4.8,
  "review_count": 342,
  "delivery_time_min": 25,
  "delivery_time_max": 35,
  "delivery_fee": 2.99,
  "min_order": 15.0
}]
```

### 2. Get restaurant details
`GET /restaurants/{restaurant_id}`

**Path parameters:** `restaurant_id` (int)

**Response 200:** `Restaurant`

**Errors**
- `404`: `{"detail": "Restaurant 99 not found"}`
- `422`: `restaurant_id` isn't an integer

### 3. Create a restaurant
`POST /restaurants`

**Auth:** `Authorization: Bearer <token>` of a `restaurant_owner` or `admin`

**Request body:** `RestaurantCreate`
```json
{
  "name": "Pasta Place",
  "cuisine": "Italian",
  "description": "Fresh handmade pasta and classic sauces.",
  "address": "45 Water St, Kelowna, BC",
  "image_url": "",
  "delivery_time_min": 20,
  "delivery_time_max": 30,
  "delivery_fee": 3.49,
  "min_order": 12.0
}
```

**Response 201:** `Restaurant`, including its new `id`

**Errors**
- `401`: no valid bearer token
- `403`: a `customer`, or a deactivated account
- `422`: a required field is missing or empty, a number is negative, or `delivery_time_max` < `delivery_time_min`

### 4. Update a restaurant
`PATCH /restaurants/{restaurant_id}`

**Path parameters:** `restaurant_id` (int)

**Auth:** `Authorization: Bearer <token>` of an `admin`, or of the `restaurant_owner` whose `restaurant_id` is this `restaurant_id`

**Request body:** `RestaurantUpdate` (only the fields to change)
```json
{ "delivery_fee": 1.99, "delivery_time_max": 40 }
```

**Response 200:** the updated `Restaurant`

**Errors**
- `401`: no valid bearer token
- `403`: any other user, or a deactivated account. A non-admin gets `403`, not `404`, for a restaurant that does not exist.
- `404`: restaurant not found
- `422`: a field has the wrong type or is empty
- `422`: after applying the update, `delivery_time_max` would be less than `delivery_time_min` (checked in the service layer against the stored restaurant)

### 5. View a restaurant's menu
`GET /restaurants/{restaurant_id}/menu`

**Path parameters:** `restaurant_id` (int)

- Categories appear in the order they first appear in the stored menu items.
- Items within a category are sorted by `id`.
- Unavailable items are included with `"is_available": false`. Use endpoint 6 with `?available=true` to get only available items.
- **Deactivated items (#87, `is_active: false`) are hidden** from this customer menu. They stay stored; see endpoint 9.
- A restaurant with no menu items returns `"categories": []`.

**Response 200:** `Menu`
```json
{
  "restaurant_id": 1,
  "restaurant_name": "Mama Rosa's Pizza",
  "categories": [
    {
      "name": "Pizza",
      "items": [
        {
          "id": 1,
          "restaurant_id": 1,
          "name": "Margherita",
          "description": "San Marzano tomato, fior di latte, basil.",
          "price": 16.99,
          "is_available": true,
          "category": "Pizza",
          "image_url": ""
        }
      ]
    },
    {
      "name": "Starters",
      "items": [
        {
          "id": 2,
          "restaurant_id": 1,
          "name": "Garlic Knots",
          "description": "Six knots with marinara.",
          "price": 7.5,
          "is_available": true,
          "category": "Starters",
          "image_url": ""
        }
      ]
    }
  ]
}
```

**Errors**
- `404`: restaurant not found
- `422`: `restaurant_id` isn't an integer

### 6. List menu items
`GET /restaurants/{restaurant_id}/menu/items`

**Path parameters:** `restaurant_id` (int)

**Query parameters**
- `available` (bool, optional): `?available=true` returns only available items

**Response 200:** `list[MenuItem]`. The list is empty if the restaurant has no items.
```json
[
  {
    "id": 1,
    "restaurant_id": 1,
    "name": "Margherita",
    "description": "San Marzano tomato, fior di latte, basil.",
    "price": 16.99,
    "is_available": true,
    "category": "Pizza",
    "image_url": ""
  },
  {
    "id": 2,
    "restaurant_id": 1,
    "name": "Garlic Knots",
    "description": "Six knots with marinara.",
    "price": 7.5,
    "is_available": true,
    "category": "Starters",
    "image_url": ""
  }
]
```

**Errors**
- `404`: restaurant not found
- `422`: invalid `restaurant_id` or `available` value

### 7. Add a menu item
`POST /restaurants/{restaurant_id}/menu/items`

**Path parameters:** `restaurant_id` (int)

**Auth:** `Authorization: Bearer <token>` of an `admin`, or of the `restaurant_owner` whose `restaurant_id` is this `restaurant_id`

**Request body:** `MenuItemCreate`
```json
{
  "name": "Garlic Knots",
  "description": "Six knots with marinara.",
  "price": 7.5,
  "is_available": true,
  "category": "Starters",
  "image_url": ""
}
```

**Response 201:** `MenuItem`, with its new `id` and `restaurant_id`

**Errors**
- `401`: no valid bearer token
- `403`: any other user, or a deactivated account. A non-admin gets `403`, not `404`, for a restaurant that does not exist.
- `404`: restaurant not found
- `422`: missing `name`, `price`, or `category`, or `price` <= 0

### 8. Update a menu item
`PATCH /restaurants/{restaurant_id}/menu/items/{item_id}`

**Path parameters:** `restaurant_id` (int), `item_id` (int)

**Auth:** `Authorization: Bearer <token>` of an `admin`, or of the `restaurant_owner` whose `restaurant_id` is this `restaurant_id`

**Request body:** `MenuItemUpdate` (only the fields to change)
```json
{ "price": 8.25, "is_available": false, "category": "Sides" }
```

**Response 200:** the updated `MenuItem`

**Errors**
- `401`: no valid bearer token
- `403`: any other user, or a deactivated account. A non-admin gets `403`, not `404`, for a restaurant that does not exist.
- `404`: the restaurant doesn't exist, the item doesn't exist, or the item belongs to a different restaurant
- `422`: a field has the wrong type, or `price` ≤ 0

**Availability (#87).** `{"is_available": false}` makes an item temporarily unavailable: customers still see it, marked unavailable, and cannot add it to a cart. `{"is_available": true}` makes it available again. `is_active` cannot be changed here (a sent `is_active` is ignored); use endpoint 9 to deactivate.

### 9. Deactivate a menu item
`DELETE /restaurants/{restaurant_id}/menu/items/{item_id}`

**Path parameters:** `restaurant_id` (int), `item_id` (int)

**Auth:** `Authorization: Bearer <token>` of an `admin`, or of the `restaurant_owner` whose `restaurant_id` is this `restaurant_id`. No request body.

**Response 204:** no body. This is a **soft delete**: the item gets `is_active = false` and is **never removed** from `menus.json`, because past orders and carts refer to its ID. It disappears from the customer menu (endpoint 5), and customers can no longer add it to a cart (409 `"<name> is not available to order right now"`). A cart that already holds it shows `is_available: false` for that line, and checkout refuses it. Deactivating an already deactivated item also returns 204.

**Errors**
- `401`: no valid bearer token
- `403`: any other user, or a deactivated account. A non-admin gets `403`, not `404`, for a restaurant that does not exist.
- `404`: the restaurant doesn't exist, the item doesn't exist, or the item belongs to a different restaurant

## Authentication

Added in M2 (#80). Signing in returns a token. Send it on requests that need a signed-in user:

```
Authorization: Bearer <token>
```

Tokens are random, are saved in `data/sessions.json` with the user's ID, and keep working after a server restart until the user signs out. That file is created at runtime and is not committed.

| Method | Path | Purpose | Success | Errors |
|---|---|---|---|---|
| POST | `/auth/login` | Sign in and get a token | 200 | 401, 403, 422, 500 |
| POST | `/auth/logout` | Sign out and delete the token | 200 | 401, 500 |

### Sign in
`POST /auth/login`

**Request body:** `LoginRequest`
```json
{ "email": "alice@foodapp.test", "password": "Password123!" }
```

**Response 200:** `LoginResponse`
```json
{ "token": "x7Qp...", "user_id": 4, "role": "customer" }
```
`role` is `customer`, `restaurant_owner` or `admin`.

**Errors**
- `401`: `{"detail": "Invalid email or password"}`. The message is the same for an unknown email and a wrong password. The response includes `WWW-Authenticate: Bearer`.
- `403`: `{"detail": "This account has been deactivated"}`. Only returned when the password is correct.
- `422`: `email` or `password` is missing, or `password` is empty
- `500`: `{"detail": "Could not complete sign in"}`. Stored user or session data could not be read or saved.

### Sign out
`POST /auth/logout`

**Headers:** `Authorization: Bearer <token>`. There is no request body.

**Response 200:** `MessageResponse`
```json
{ "message": "Signed out" }
```

**Errors**
- `401`: `{"detail": "Not authenticated"}` if the header is missing or is not a bearer token, or `{"detail": "Invalid session token"}` if the token is unknown or already signed out. The response includes `WWW-Authenticate: Bearer`.
- `500`: `{"detail": "Could not complete sign out"}`. Stored session data could not be read or saved.

### Protected endpoints

Added in M2 (#81). An endpoint that needs a signed-in user checks the token before anything else, including the request body:

| Situation | Status | Body |
|---|---|---|
| No `Authorization` header, a scheme other than `Bearer`, or an empty token | 401 | `{"detail": "Not authenticated"}` |
| The token is unknown or signed out, or its user no longer exists | 401 | `{"detail": "Invalid session token"}` |
| The user's account is deactivated (also if it was deactivated after signing in) | 403 | `{"detail": "This account has been deactivated"}` |
| The endpoint is limited to certain roles and the user has another one | 403 | `{"detail": "You do not have permission to do this"}` |
| The endpoint changes one restaurant or its menu, and the user is not an admin or that restaurant's owner (#82) | 403 | `{"detail": "You do not have permission to change this restaurant"}` |
| Stored user or session data cannot be read | 500 | `{"detail": "Could not verify the sign-in"}` |

Every 401 includes `WWW-Authenticate: Bearer`. Protected endpoints show the `HTTPBearer` security scheme in OpenAPI.

## Customer Accounts

Added in M2 (#83-#86). Customers are stored in `data/users.json` as users with role `customer`. Responses use `CustomerResponse`, which never includes the password or its hash:

```json
{ "id": 4, "email": "alice@foodapp.test", "name": "Alice Smith", "phone": "250-555-0101", "delivery_address": "123 Main St, Kelowna, BC", "is_active": true }
```

| Method | Path | Who | Purpose | Success | Errors |
|---|---|---|---|---|---|
| POST | `/customers` | anyone | Register a customer | 201 | 409, 422, 500 |
| GET | `/customers/me` | customer | View my profile | 200 | 401, 403, 500 |
| PATCH | `/customers/me` | customer | Update my details and delivery address | 200 | 401, 403, 422, 500 |
| POST | `/customers/me/deactivate` | customer | Deactivate my account | 200 | 401, 403, 500 |
| GET | `/customers/{customer_id}` | admin | View any customer | 200 | 401, 403, 404, 422, 500 |
| POST | `/customers/{customer_id}/deactivate` | admin | Deactivate any customer | 200 | 401, 403, 404, 409, 422, 500 |

401 and 403 follow [Protected endpoints](#protected-endpoints). The 500 body is always `{"detail": "Could not access customer data"}`.

### Register a customer
`POST /customers`

**Request body:** `CustomerCreate`. `name`, `email` and `password` are required; `phone` and `delivery_address` default to `""`.
```json
{ "name": "Dana Park", "email": "dana@example.com", "password": "longenough", "delivery_address": "1 Lake Rd" }
```
The role is always `customer`. Sending any other field, including `role`, returns 422. The email is stored lowercase, and the password is stored only as a hash. The customer can sign in straight away.

**Errors**
- `409`: `{"detail": "An account with this email already exists"}` (case is ignored)
- `422`: empty `name`, invalid email, password shorter than 8 characters, or an unknown field

### Update my details
`PATCH /customers/me`

**Request body:** `CustomerUpdate`, any of `name`, `phone`, `delivery_address`. A field left out or sent as `null` keeps its value. `phone` may be set to `""`; `name` and `delivery_address` may not be empty.

**Decision (#85):** any other field (`email`, `role`, `id`, `is_active`, ...) is **rejected with 422**, not silently ignored, so a client finds out at once that it cannot change it.

### Deactivate an account
`POST /customers/me/deactivate` (customer) or `POST /customers/{customer_id}/deactivate` (admin). No request body. Returns the customer with `is_active: false`.

The account is kept, not deleted, so its ID, carts and orders stay valid. Afterwards, signing in returns 403 and the customer's existing tokens get 403 on every protected endpoint.

**Decision (#86):** deactivating an already-deactivated customer through the admin endpoint returns **409** `{"detail": "Customer 6 is already deactivated"}`. Through `/customers/me` it cannot happen: the deactivated customer's token already gets 403.

## Shopping Cart

Added in M2 (#88-#92). Every cart endpoint needs a signed-in, active **customer**: no token is 401; another role or a deactivated account is 403 (see [Protected endpoints](#protected-endpoints)). Each customer has at most one active cart, saved in `data/carts.json`.

| Method | Path | Purpose | Success | Errors |
|---|---|---|---|---|
| GET | `/cart` | Get my active cart (created empty the first time) | 200 | 401, 403, 500 |
| POST | `/cart/items` | Add an item (or increase its quantity) | 200 | 401, 403, 404, 409, 422, 500 |
| PATCH | `/cart/items/{menu_item_id}` | Set the quantity of an item in the cart | 200 | 401, 403, 404, 422, 500 |
| DELETE | `/cart/items/{menu_item_id}` | Remove an item | 200 | 401, 403, 404, 500 |
| DELETE | `/cart/items` | Clear the cart | 200 | 401, 403, 500 |

Every endpoint returns the whole cart as `CartResponse`. The 500 body is `{"detail": "Could not access cart data"}`.

### CartResponse
```json
{
  "id": 1, "customer_id": 4, "restaurant_id": 1, "status": "active",
  "items": [
    { "menu_item_id": 1, "name": "Kung Pao Chicken", "unit_price": 15.5, "quantity": 2, "line_total": 31.0, "is_available": true }
  ],
  "subtotal": 31.0, "delivery_fee": 4.99, "total": 35.99
}
```

**Prices (#92).** The stored cart holds only `menu_item_id` and `quantity`. Every response reads the **current** menu price, so a price change shows on the next request. `line_total = unit_price × quantity`, `subtotal` is the sum of the lines, and `total = subtotal + delivery_fee`. The delivery fee is a flat $4.99 (`settings.delivery_fee` in `app/core/config.py`) and $0 for an empty cart. All amounts are calculated with `Decimal` and rounded to cents in `app/services/pricing.py`, which checkout should reuse. Requests have no price fields; an extra `price` field is ignored. `is_available` is false if the item has since become unavailable or been deactivated.

### Add an item
`POST /cart/items` with `CartItemAdd`: `{ "menu_item_id": 1, "quantity": 2 }`. `quantity` defaults to 1.

| Rule | Status | Example `detail` |
|---|---|---|
| `quantity` must be a whole JSON number from 1 to 20 (`"2"`, `2.5` and `true` are refused) | 422 | field error list |
| The line can't go above 20 in total | 422 | `"You can have at most 20 of one item in your cart (you already have 18)"` |
| The menu item must exist | 404 | `"Menu item 99 not found"` |
| The item must be available and not deactivated (`is_active`) | 409 | `"Beef Chow Mein is not available to order right now"` |
| All items must come from one restaurant. An empty cart takes the restaurant of its first item | 409 | `"Your cart can only contain items from one restaurant. Clear it or remove those items first."` |

Adding an item that is already in the cart increases its quantity. A refused request leaves the stored cart unchanged.

### Change, remove, clear
- `PATCH /cart/items/{menu_item_id}` with `{ "quantity": 3 }` sets the quantity (1 to 20, else 422).
- `DELETE /cart/items/{menu_item_id}` removes the line. Removing the last line resets `restaurant_id` to null.
- `DELETE /cart/items` empties the cart and resets `restaurant_id`, keeping the same cart `id`.
- An item that is not in the cart returns 404 `"Menu item 3 is not in your cart"`.

### MenuItem.is_active
Added to `MenuItem` for the cart rule above; it defaults to `true`, so existing data still loads. An owner or admin deactivates an item with `DELETE /restaurants/{restaurant_id}/menu/items/{item_id}` (#87), which also hides it from the customer menu.

## Existing Endpoints (unchanged from M0)

| Method | Path | Response |
|---|---|---|
| GET | `/health` | 200 `{"status": "ok"}` |
| GET | `/docs` | OpenAPI documentation |