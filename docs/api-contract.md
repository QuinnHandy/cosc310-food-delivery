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
| 3 | POST | `/restaurants` | Create a restaurant | 201 | 422 |
| 4 | PATCH | `/restaurants/{restaurant_id}` | Update a restaurant | 200 | 404, 422 |
| 5 | GET | `/restaurants/{restaurant_id}/menu` | View a restaurant's menu | 200 | 404, 422 |
| 6 | GET | `/restaurants/{restaurant_id}/menu/items` | List menu items | 200 | 404, 422 |
| 7 | POST | `/restaurants/{restaurant_id}/menu/items` | Add a menu item | 201 | 404, 422 |
| 8 | PATCH | `/restaurants/{restaurant_id}/menu/items/{item_id}` | Update a menu item | 200 | 404, 422 |

Every endpoint can also return 500 if the stored data can't be read.

## Endpoints

### 1. List, search, and filter restaurants
`GET /restaurants`

Returns all restaurants sorted by `id`. Optional query parameters narrow the results. Filters combine with AND.

**Query parameters**
- `q` (str, optional): case-insensitive partial match on name **or** cuisine, e.g. `?q=pizza`. An empty `q` is ignored: `?q=` returns all restaurants.
- `cuisine` (str, optional): case-insensitive exact match on cuisine, e.g. `?cuisine=Italian`

**Response 200:** `list[Restaurant]`. The list is empty if nothing matches; that isn't an error.
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
- `422`: a required field is missing or empty, a number is negative, or `delivery_time_max` < `delivery_time_min`

### 4. Update a restaurant
`PATCH /restaurants/{restaurant_id}`

**Path parameters:** `restaurant_id` (int)

**Request body:** `RestaurantUpdate` (only the fields to change)
```json
{ "delivery_fee": 1.99, "delivery_time_max": 40 }
```

**Response 200:** the updated `Restaurant`

**Errors**
- `404`: restaurant not found
- `422`: a field has the wrong type or is empty
- `422`: after applying the update, `delivery_time_max` would be less than `delivery_time_min` (checked in the service layer against the stored restaurant)

### 5. View a restaurant's menu
`GET /restaurants/{restaurant_id}/menu`

**Path parameters:** `restaurant_id` (int)

- Categories appear in the order they first appear in the stored menu items.
- Items within a category are sorted by `id`.
- Unavailable items are included with `"is_available": false`. Use endpoint 6 with `?available=true` to get only available items.
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
- `404`: restaurant not found
- `422`: missing `name`, `price`, or `category`, or `price` <= 0

### 8. Update a menu item
`PATCH /restaurants/{restaurant_id}/menu/items/{item_id}`

**Path parameters:** `restaurant_id` (int), `item_id` (int)

**Request body:** `MenuItemUpdate` (only the fields to change)
```json
{ "price": 8.25, "is_available": false, "category": "Sides" }
```

**Response 200:** the updated `MenuItem`

**Errors**
- `404`: the restaurant doesn't exist, the item doesn't exist, or the item belongs to a different restaurant
- `422`: a field has the wrong type, or `price` ≤ 0

## Existing Endpoints (unchanged from M0)

| Method | Path | Response |
|---|---|---|
| GET | `/health` | 200 `{"status": "ok"}` |
| GET | `/docs` | OpenAPI documentation |