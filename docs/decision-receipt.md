# 1. Decision Receipt: Layered architecture (route → service → repository)

- **Date:** 2026-10-16
- **Status:** Accepted
- **Decided by:** Team 11 (Quinn Handy, Asher Nathan, Timo Clement, Samuel Mwanduka)
- **Milestone:** M1, First Vertical Slice

## Context
For Milestone 1, we are building a food delivery backend that handles restaurants, search and filtering, menus, and menu items. We are also developing a basic web frontend. Since four team members are working on the project, we need a structure that allows us to develop different features without constantly editing the same files.

Our main priorities are maintainability, testability, and simplicity. We want the code to be easy to understand and update as we add features in later milestones. We also need to test repository operations and failure cases using pytest, while following the course requirement to store data in JSON/CSV files rather than a database.

Our four main requirements when making this decision:
- **Maintainability:** If we need to change how data is read or written, we can make most of those changes in the repository layer without rewriting the routes.
- **Testing:** We can use app.dependency_overrides and tmp_path to test repository behaviour with temporary JSON files without affecting the project's actual data.
- **Easy teamworking** The layered structure allows team members to work on different features and reduces the likelihood of merge conflicts.
- **Separation of concerns:** Each layer has a specific responsibility, keeping HTTP handling, business logic, and file storage separate.

## Options considered
1. **Layered architecture (chosen):** Routes handle HTTP requests, services contain the business logic, and repositories handle reading and writing JSON files.
2. **Everything in route handlers:** Each endpoint handles requests, business logic, and JSON file operations directly. This would require less setup initially, but could make the code harder to maintain..
3. **Event-driven architecture with separate services:** Restaurants and menus would be handled by separate services that communicate through events. Although this approach can make a system more extensible, it introduces more complexity than we need for M1.

## Decision
We decided to use a three-layer structure inside one FastAPI application:
- `app/api/routes/`: Handles incoming requests and returns appropriate HTTP status codes, such as 404, 422, and 500.
- `app/services/`: Handles business logic such as search and filtering. For simple operations (get, create, update), services currently pass through to the repository, which keeps a place for future logic like ordering rules.
- `app/repositories/`: Handles reading and writing JSON files. Repositories also validate records loaded from JSON against the models, check menu items for orphaned restaurant IDs, and apply partial updates. Writes use a temporary file and os.replace to reduce the risk of incomplete file updates.

Request validation is done by the Pydantic schemas in `app/schemas/`, and FastAPI returns 422 automatically when it fails.

We will use FastAPI's Depends to provide the required services and repositories to the routes. This also makes it easier to replace dependencies when testing different parts of the application.

## Reasons
- **Separation of concerns:** Each layer has a specific responsibility, so HTTP handling, business logic, and file storage do not become mixed together. This follows the layered architecture discussed in class.
- **Easier maintenance:** If we need to change how files are read or written, we can make most of those changes in the repository layer. This follows the lecture's point that changes to storage or the user interface can be contained behind interfaces.
- **Testability:** We can override get_restaurant_repository using app.dependency_overrides and provide a temporary JSON file through tmp_path. This allows us to test repository operations without changing the actual project data.
- **Parallel development:** We can work on different layers and features, which should reduce conflicts when combining our code.
- We rejected the second option because putting everything inside route handlers would mix HTTP requests with business logic and file operations. This could make future changes more difficult because the same code might need to be updated in several endpoints.

- We also rejected the event-driven approach because it would introduce additional challenges, including eventual consistency and more complicated debugging. As discussed in the lecture, event-driven architecture can improve extensibility, but its benefits do not justify the extra complexity for our current project.

## Consequences
**Benefits**
- Each layer has a clear purpose, making the code easier to understand and maintain.
- File operations are kept separate from the routes and business logic.
- Temporary files and dependency overrides make repository testing easier.
- Team members can work on separate parts of the application more independently.

**Trade-offs / costs**
- **Extra indirection:** simple features such as "list restaurants" need code in three files.
- **Possible boundary violations:** A route could bypass the service layer and access a repository directly. We will use code reviews to help ensure that everyone follows the agreed structure.
- **Performance vs maintainability:** The extra calls between layers introduce some overhead, but we expect this to be negligible for a our project. JSON/CSV file storage also has limitations when handling concurrent writes and maintaining data integrity, but we will work within the storage requirements set by the course.
- **Logic in the repository layer:** Some data-integrity logic (orphan checks, merging partial updates) lives in the repository layer rather than the service layer. This keeps it next to the file data, but it makes the repositories do more than just storage. We will revisit this if the services grow.

**Revisit when:** We add more complex features, such as orders, carts, and deliveries, or if we encounter problems with the current architecture

---

# 2. Decision Receipt: Server-assigned IDs (max + 1)

- **Date:** 2026-10-16
- **Status:** Accepted
- **Decided by:** Team 11

## Context

Restaurants and menu items need unique IDs so the API and JSON files can identify the correct records. Menu items also have a `restaurant_id` to show which restaurant they belong to. Once an ID is assigned, it should stay the same so these references remain valid.

## Options considered

1. **Server-assigned IDs using max(existing IDs) + 1 (chosen).**
2. **Client-supplied IDs:** the frontend sends an ID when creating a record.
3. **Reusing deleted IDs:** use numbers from records that have been removed.

## Decision

The repository assigns IDs when a new record is created by finding the highest existing ID and adding 1. If there are no existing records, the first ID is 1. The client does not need to provide an ID when creating a restaurant or menu item.

## Reasons

- The server controls ID assignment, which reduces the chance of clients choosing IDs that are already in use.
- Keeping IDs stable helps menu items continue to reference the correct restaurant.
- Reusing IDs could cause confusion if an old reference points to a different record. With max + 1, reusing IDs is avoided as long as records are not deleted.
- This approach is simple to implement and works with the JSON files used in M1.

## Consequences

**Benefits:** IDs are predictable, easy to understand, and straightforward to manage in the JSON files.

**Trade-offs / costs**

- If two create requests run at the same time, they could calculate the same next ID. Our current approach does not prevent this, but it is an acceptable limitation for the current M1 setup.
- IDs are sequential and easy to guess. They are used to identify records, not to provide security or control access.
- max + 1 only avoids reusing IDs while records are never deleted. If the record with the highest ID were deleted, the next create would get that same ID again. That would bring back the problem option 3 was rejected for. This can't happen in M1 because there is no delete.

**Revisit when:** we add delete endpoints (switch to a stored next_id counter so IDs are never reused), the project needs to support concurrent writers, or the current ID assignment method causes problems.

---

# 3. Decision Receipt: PATCH for Updates

- **Date:** 2026-10-16
- **Status:** Accepted
- **Decided by:** Team 11

## Context

The restaurant owner needs to be able to edit an existing restaurant. Sometimes only one field needs to change, such as the name or cuisine. Requiring the frontend to send the entire record for every small change would make updates less convenient.

## Options considered

1. **PATCH with partial updates (chosen):** only the fields included in the request are changed.
2. **PUT to replace the whole record:** the client sends the complete record, including fields that have not changed.

## Decision

We use `PATCH /restaurants/{restaurant_id}` with a `RestaurantUpdate` model. The fields `name` and `cuisine` are optional, so the client can send just the field it wants to change.

In `restaurant_repository.py`, the existing restaurant data is combined with the supplied fields using `changes.model_dump(exclude_unset=True)`. This keeps fields that were not included in the request unchanged. Provided names and cuisine values must also pass validation, including the minimum length of one character.

## Reasons

- It matches the owner page use case because an owner can change one field without resending the entire restaurant record.
- It reduces the chance of accidentally overwriting other fields with outdated values from a form.
- The update model makes it clear which fields can be changed and what validation they must pass.
- The repository handles the update to the JSON data, keeping file operations separate from the route and service logic.

## Consequences

**Benefits:** smaller requests, fewer accidental changes to unrelated fields, and a `404` response when the restaurant ID does not exist.

**Trade-offs / costs**

- Fields that are not sent remain unchanged. In the current schema, an empty name or cuisine is rejected rather than used to clear the field.
- PATCH is designed for partial updates. A client that wants to replace the full record must send all the relevant fields.
- Two updates to the same record can still overwrite each other if they happen close together. M1 does not include version checking or conflict detection.

**Revisit when:** we need to support clearing fields, detect conflicting updates, or change how full-record updates should work.


---

# M2.1 Decision Receipt (Asher Nathan): One shared JSON store for every repository

> Status: Accepted and implemented

- **Date:** 2026-11-19
- **Status:** Proposed (PR for #108)
- **Decided by:** Asher Nathan; to be reviewed by the team
- **Milestone:** M2, Integrated Core System
- **Issue / PR / tests:** #108 / PR for #108 / `tests/test_json_store.py`

## Weakness found during integration
M2 added three new kinds of stored data (users, sessions, carts), and orders are next. Each repository had its own copy of the same code: read the file, parse JSON, check it is a list, validate every record with a Pydantic model, write it back through a temp file, and compute `max(id) + 1`. Before this change that code was repeated across `restaurant_repository.py`, `menu_repository.py`, `cart_repository.py` and `session_repository.py`, and every new repository would have copied it again.

Integration also exposed a real defect in the copied save code. `write_json_atomic` only caught `OSError`, so a record that could not be serialized raised a raw `TypeError` (an unhandled 500 instead of our `DataAccessError` → 500 with a message), and it left a stray `.tmp` file in `data/`. A failed `os.replace` also left its temp file behind. Checked against the old code at `abe81d9`: `raised TypeError … stray temp files: ['tmph1_ns4xx.tmp']`.

## Options considered
1. **Shared `JsonStore` helper (chosen):** one generic class for load/validate/save/next-ID; each repository keeps only its own rules.
2. **Abstract base repository class:** repositories inherit `get`, `add`, `update`. Rejected for now: our repositories differ a lot (menu items are scoped to a restaurant, carts have one-active-per-customer, users check emails and restaurant links), so a base class would need many hooks or overrides.
3. **Leave the copies:** least work today, but every new repository (orders next) copies the code and its defect again.

## Decision
`app/repositories/json_store.py` contains `JsonStore(path, Model, label, missing_ok=False, dump=None)` with `load()`, `save()` and `require_unique_ids()`, plus `next_id()`, `write_json_atomic()` and `DataAccessError`. The restaurant, menu, cart and session repositories now use it. `restaurant_repository.py` still re-exports `DataAccessError` and `write_json_atomic`, so no other import had to change. `write_json_atomic` now serializes before it creates the temp file, and removes the temp file if the swap fails.

## Evidence
- **Before → after:** the four repositories went from 324 to 204 lines (diff −151 / +30); the shared `json_store.py` is 124 lines including docs.
- **Behaviour unchanged:** the full existing suite passed with no test changes (432 before → 432 after the refactor, then 448 with the new tests).
- **Tests for the new code:** `tests/test_json_store.py`: round trip, stable and never-reused IDs, **failed serialization leaves the old file intact and no temp file**, **failed swap leaves the old file and no temp file**, missing-file rules, invalid-file errors, and a check that the four repositories no longer contain their own `json.loads`/`tempfile` code.

## Consequences
- New repositories (orders, #93) need only their own rules plus a `JsonStore` line.
- `UserRepository` still has its own copy, because it writes `id` first and #79/#81 were in review. Moving it over (with `dump=`) is a small follow-up.
- Error messages now come from one place, so they read the same for every data file.

---

# M2.1 Decision Receipt (Quinn Handy): One home for the rules the cart and checkout share

> Status: Accepted and implemented

- **Date:** 2026-11-20
- **Status:** Proposed (PR for #109)
- **Decided by:** Quinn Handy; to be reviewed by the team
- **Milestone:** M2, Integrated Core System
- **Issue / PR / tests:** #109 / PR for #109 / `tests/test_shared_ordering_rules.py`

## Weakness found during integration
The cart (#89–#92) and checkout (#94) were built in parallel, and each wrote its own copy of two rules:

- **"Is this an active customer?"** was `CartService._require_active_customer` and `CheckoutService._require_active_customer`.
- **"Can this item be ordered?"** was `if not item.is_available or not item.is_active` in `CartService.add_item`, and the same check again in `CheckoutService._current_items`. It also appeared a third time as `item.is_available and item.is_active` in the cart response.

The copies had already drifted. Checkout re-read the customer from storage, but the cart only looked at the `User` object it was handed. Through the service, a customer deactivated after signing in could still add to their cart, even though checkout refused them. We checked this against `main` at `5cf3b3e`: `add_item` with a stale user succeeded after `is_active` was set to false. The checkout route also had to catch two different exceptions for the same rule (`CheckoutNotAllowedError` and the cart's `CustomerNotAllowedError`).

## Options considered
1. **Put each rule on the service that owns the data (chosen):** `CustomerService.require_active_customer` and `MenuService.get_orderable_item` / `is_orderable`. The cart and checkout get those services through their constructors.
2. **A separate `rules.py` module of free functions:** less wiring, but the customer check needs to read storage. That would mean passing repositories into plain functions, or the rule ending up somewhere other than the service that owns customers.
3. **Leave the copies and add tests for both:** the least change, but the next rule change (e.g. "restaurant closed") would have to be made in two places again.

## Decision
- `CustomerService.require_active_customer(user)` re-reads the account and raises `CustomerNotAllowedError` for another role, an unknown account or a deactivated one. The exception moved to `customer_service.py`.
- `MenuService.is_orderable(item)` is the single definition of orderable (active and available). `MenuService.get_orderable_item(id)` raises `MenuItemNotFoundError` or `MenuItemUnavailableError`. The exception moved to `menu_service.py`.
- `CartService(cart_repository, menu_service, customer_service, fee)` and `CheckoutService(customer_service, cart_service, menu_service, ...)` call those methods instead of their own copies. Checkout still turns the errors into `CheckoutNotAllowedError` / `CartChangedError`, so every checkout refusal stays a `CheckoutError` and the API responses (403/409) don't change.
- `cart_service.py` still re-exports both exceptions, so the routes and tests that import them from there keep working.

## Evidence
- **Behaviour unchanged:** all 648 existing tests passed after the refactor. The only test edits were the new constructor arguments in `test_cart_service.py` and `test_checkout_service.py`.
- **New tests:** `tests/test_shared_ordering_rules.py` has 19 tests:
  - each shared method on its own
  - the cart and checkout refusing an unavailable item, a deactivated item, a customer deactivated after sign-in and an owner, **with the same message**
  - a regression test for the stale deactivated customer
  - a check that `cart_service.py` and `checkout_service.py` no longer contain their own `is_available` / `.is_active` / role checks
- **Full suite:** 667 passed.

## Consequences
- A rule change, such as adding "restaurant is closed", now happens in one method, and both the cart and checkout pick it up.
- Cart operations now re-read the customer each time, which is one extra small file read per request. That's acceptable for our JSON storage, and it's what makes the stale-user case safe.
- `CartService` now depends on two more services. The wiring lives in `app/api/dependencies.py`, from #106, so the routes didn't change.

---

# M2.1 Decision Receipt (Samuel Mwanduka): One place for dependency providers

> Status: Accepted and implemented

- **Date:** 2026-11-20
- **Status:** Implemented (PR #134); team confirmation pending
- **Decided by:** Samuel Mwanduka; to be reviewed by the team
- **Milestone:** M2, Integrated Core System
- **Issue / PR / tests:** #106 / PR #134 / `tests/test_dependency_providers.py`

## Weakness found during integration

As M2 added customer accounts, carts, checkout, and orders, dependency providers became spread across multiple route files. For example, `get_menu_repository` and `get_menu_service` were defined in both `restaurants.py` and `menus.py`.

Some route files also imported dependency providers from other routes. This created unnecessary coupling and meant that changing a service could require updates in multiple files. It also made testing harder because overriding one provider would not necessarily replace the other copies.

## Options considered

1. **Move all providers into `app/api/dependencies.py` (chosen):** One shared location for creating repositories and services, while routes import what they need.
2. **Keep providers in individual route files:** Requires less refactoring but leaves duplicated code and makes dependencies harder to manage.
3. **Use a separate dependency container:** More flexible for a larger application, but adds complexity that is unnecessary for our project.

## Decision

`app/api/dependencies.py` now contains the repository and service providers for restaurants, menus, users, authentication, customers, carts, checkout, and orders.

The route modules import these shared providers instead of creating their own. Existing authentication dependencies remain in the same module.

Tests can now override a dependency in one place using FastAPI's `app.dependency_overrides`, without needing to replace multiple definitions.

## Evidence

- **Before → after:** Providers were spread across several route files. Duplicated menu providers in `restaurants.py` and `menus.py` were consolidated into `dependencies.py`.
- **Tests:** `tests/test_dependency_providers.py` verifies that route modules no longer define their own repository or service providers.
- **Behaviour unchanged:** Existing test assertions did not need changes. Relevant imports were updated, and the full pytest suite passed after the refactor.
- **PR:** #134 replaced the earlier #131 implementation after merge conflicts.

## Consequences

- New services can be added without creating dependency providers in multiple route files.
- Tests are easier to maintain because dependencies can be overridden in one location.
- `dependencies.py` is now responsible for more service construction, so the file may become larger as the application grows.
- If the system becomes significantly more complex, the providers could be split into smaller modules.

---

# M2.1 Decision Receipt (Timo Clement): One handler for domain errors

> Status: Accepted and implemented

- **Date:** 2026-11-20
- **Status:** Implemented (PR #141); team confirmation pending
- **Decided by:** Timo Clement; to be reviewed by the team
- **Milestone:** M2, Integrated Core System
- **Issue / PR / tests:** #107 / PR #141 / `tests/test_domain_errors.py`

## Weakness found during integration

Before the refactor, each API route manually caught exceptions from services and repositories and converted them into FastAPI `HTTPException` responses.

As M2 added customer accounts, carts, checkout, and orders, more error types were introduced, such as unauthorized access, unavailable items, invalid states, and data access failures.

This led to repeated `try/except` blocks across route files. It also increased the risk of different endpoints returning inconsistent status codes or error messages for similar problems.

## Options considered

1. **Centralized domain error handling (chosen):** Services raise shared domain exceptions, and one handler converts them into HTTP responses.
2. **Keep individual route-level exception handling:** Requires fewer initial changes but continues duplicating error-handling logic.
3. **Raise `HTTPException` directly from services:** Removes some route code but couples business logic to FastAPI.

## Decision

Added `app/core/errors.py` containing shared domain exceptions, including `UnauthorizedError`, `ForbiddenError`, `NotFoundError`, `ConflictError`, `BusinessRuleError`, and `DataAccessError`.

A centralized exception handler in `app/main.py` converts these errors into the appropriate HTTP status codes.

Domain error responses now use the same format:

`{"detail": "Error message", "code": "error_code"}`

Services and repositories raise domain errors, while routes no longer need to manually translate them into HTTP exceptions. The shared OpenAPI `ErrorResponse` model was also updated.

FastAPI request-validation errors continue to use their standard validation response format.

## Evidence

- **Before → after:** Individual route files contained repeated exception handling and HTTP conversions. These are now handled centrally in `app/main.py`.
- **Tests:** `tests/test_domain_errors.py` verifies the mappings for 401, 403, 404, 409, 422, and 500 responses.
- **Code checks:** Verified that the old `HTTPException`, `_data_error`, and `_call` handling patterns were removed from `app/api`.
- **Full suite:** 658 tests passed with one unrelated deprecation warning in PR #141.
- **PR:** #141 also updated the shared OpenAPI error schema and examples.

## Consequences

- All endpoints return consistent domain error responses, making API behaviour easier to understand and test.
- Routes are simpler because they no longer need repeated exception-handling blocks.
- Business logic is less dependent on FastAPI because services raise domain exceptions instead of HTTP exceptions.
- Changes to the centralized handler can affect multiple endpoints, so maintaining comprehensive error tests is important.
- New domain error categories will need to be added to the shared exception system.