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

