# Decision Receipt: Layered architecture (route → service → repository)

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
- `app/services/`: Handles business logic, including search, filtering, validation, and checks for orphaned records.
- `app/repositories/`: Handles reading and writing JSON files. Writes use a temporary file and os.replace to reduce the risk of incomplete file updates.

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

**Revisit when:** We add more complex features, such as orders, carts, and deliveries, or if we encounter problems with the current architecture. We will review whether the existing layers still meet our needs while continuing to follow the course's JSON/CSV storage requirements.