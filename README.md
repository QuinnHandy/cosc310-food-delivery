# cosc310-food-delivery
Team 11



## Requirements: 
    Python 3.13 or newer
    Git

## Setup

### 1. Clone the repository
```bash
git clone https://github.com/QuinnHandy/cosc310-food-delivery.git
cd cosc310-food-delivery
```

### 2. Create and activate a virtual environment
macOS / Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

Windows (PowerShell):
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

## Running the Application
```bash
uvicorn app.main:app --reload
```
The API runs at http://127.0.0.1:8000
The customer web page is at http://127.0.0.1:8000/ (browse restaurants, search by name as you type, filter by cuisine, and click one to see its details).
The restaurant owner page is at http://127.0.0.1:8000/owner (add a restaurant, or click Edit on one to change it). 

## API Endpoints
| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check, returns 200 `{"status": "ok"}` |
| GET | `/restaurants` | Lists all restaurants sorted by ID. Optional query parameters: `name` (partial match, ignores case) and `cuisine` (exact match, ignores case). No matches returns 200 with `[]` |
| POST | `/restaurants` | Create a restaurant (`name`, `cuisine`). Returns 201 with the new restaurant |
| GET | `/restaurants/{restaurant_id}` | Details for one restaurant (404 if the ID doesn't exist) |
| PATCH | `/restaurants/{restaurant_id}` | Update a restaurant's `name` and/or `cuisine` (404 if the ID doesn't exist) |
| GET | `/restaurants/{restaurant_id}/menu` | A restaurant's menu items sorted by ID (404 if the restaurant doesn't exist; `items` is `[]` if it has none) |
| POST | `/restaurants/{restaurant_id}/menu` | Add a menu item (`name`, `price`, `category`, plus optional `description`, `is_available`, `image_url`). Returns 201 with the new item (404 if the restaurant doesn't exist) |
| POST | `/auth/login` | Sign in with `email` and `password`. Returns 200 with `token`, `user_id` and `role` (401 if the details are wrong, 403 if the account is deactivated) |
| POST | `/auth/logout` | Sign out using `Authorization: Bearer <token>`. Returns 200 with a message (401 if the token is missing or not valid) |

Web pages (HTML, not part of the API docs):
| Method | Path | Description |
|---|---|---|
| GET | `/` | Customer web page |
| GET | `/owner` | Restaurant owner page |

Search and filter examples:
- `/restaurants?cuisine=italian`: only Italian restaurants
- `/restaurants?name=piz`: restaurants whose name contains "piz"
- `/restaurants?name=piz&cuisine=italian`: both must match

Interactive API docs: http://127.0.0.1:8000/docs
The full M1 API contract (all endpoints, models, and status codes) is in [docs/api-contract.md](docs/api-contract.md).

## Data
- `data/restaurants.json`, `data/menus.json` and `data/users.json` hold the sample data, and they are where changes made through the app (API or web pages) are saved.
- `data/users.json` stores only salted password hashes (PBKDF2-SHA256), never plain passwords.
- Saved changes survive a restart of the server. Writes go to a temporary file first and then replace the original, so a crash never leaves a half-written file.
- IDs are assigned by the server (highest existing ID + 1) and never change, so menu items keep pointing at the right restaurant.
- The data location can be changed with the `APP_DATA_DIR` environment variable.
- Creating or editing data through the app changes these tracked files. To reset them to the committed sample data, run `git checkout -- data/`.

## Demo accounts
The seed data in `data/users.json` has these accounts. They all use the demo password `Password123!`.

| Email | Role | Notes |
|---|---|---|
| `admin@foodapp.test` | admin | |
| `owner1@foodapp.test` | restaurant owner | Manages Golden Dragon (restaurant 1) |
| `owner2@foodapp.test` | restaurant owner | Manages Spice Garden (restaurant 2) |
| `alice@foodapp.test` | customer | Has a phone number and delivery address |
| `bob@foodapp.test` | customer | Has a phone number and delivery address |
| `carol@foodapp.test` | customer | Deactivated account (`is_active: false`), for the deactivated-customer demo |

To sign in, open http://127.0.0.1:8000/docs, run `POST /auth/login` with one of these accounts and copy the `token` from the response. Click **Authorize**, paste the token (without the word `Bearer`) and confirm, and `/docs` will send it with requests such as `POST /auth/logout`. Tokens are saved in `data/sessions.json`, which is created when the app runs and is ignored by git.

## Where authentication and authorization are enforced
Both are checked in the backend, in two FastAPI dependencies in [app/api/dependencies.py](app/api/dependencies.py). The web pages are never trusted to decide who may do what.

- **Authentication (who is calling): `get_current_user`.** It reads `Authorization: Bearer <token>`, looks the token up in `data/sessions.json` and loads that session's user from `data/users.json`. The lookup rules live in `AuthService.get_user_for_token` ([app/services/auth_service.py](app/services/auth_service.py)).
- **Authorization (what they may do): `require_role(*roles)`.** It builds a dependency that runs `get_current_user` and then checks the user's role. A route opts in with `Depends(require_role("admin"))`.

| Situation | Response |
|---|---|
| No `Authorization` header, a scheme other than `Bearer`, or an empty token | `401` with `WWW-Authenticate: Bearer` |
| Token is not in `sessions.json` (never issued, or signed out), or its user no longer exists | `401` with `WWW-Authenticate: Bearer` |
| Valid token but the account is deactivated (also if it was deactivated after signing in) | `403` |
| Valid token and active account, but the role is not allowed | `403` |
| Valid token, active account and allowed role | The request goes ahead |
| Stored user or session data cannot be read | `500` with a fixed message that does not quote stored data |

The checks run before the request body is validated, so a request without a valid token gets `401` even if its body is also wrong. In `/docs`, routes that use these dependencies show a padlock, and **Authorize** sends the token (see Demo accounts above). `tests/test_auth_dependencies.py` covers each row of the table on a small test-only app, using temporary data.

## Repository Structure
```
app/
  api/routes/      # FastAPI routes (HTTP layer)
  services/        # Business logic
  repositories/    # Data access (reads and writes JSON)
  schemas/         # Pydantic models
  core/            # Configuration
  static/          # Web frontend (HTML and JS)
  main.py          # App entry point
data/              # JSON data files
docs/              # API contract, decision receipts, provenance
tests/             # pytest test suite
scrum/             # Team agreement and sprint notes
.github/workflows/ # CI (GitHub Actions)
```

## Running Tests
pytest and httpx are included in `requirements.txt`, so no extra install is needed. Run all tests with

```bash
python -m pytest
```

or a single test file with

```bash
python -m pytest tests/test_restaurant_search.py -v
```

Tests that write data use temporary JSON files (`tmp_path` and `app.dependency_overrides`), so running the suite never changes the files in `data/`.

The test suite covers:
- **API endpoints**
  - `/health` (`test_health.py`)
  - listing restaurants and unknown paths (`test_restaurant.py`)
  - search and filter by `name` and `cuisine`, including blank and no-match cases (`test_restaurant_search.py`)
  - restaurant details, 404 and 422 cases (`test_restaurant_details.py`)
  - creating a restaurant (`test_create_restaurant.py`)
  - updating a restaurant (`test_update_restaurant.py`)
  - create → update → get in one flow (`test_restaurant_management_flow.py`)
  - viewing a restaurant's menu (`test_restaurant_menu.py`)
  - adding a menu item (`test_add_menu_item.py`)
  - the auth dependencies: 401 and 403 cases for `get_current_user` and `require_role` (`test_auth_dependencies.py`)
- **Services:** search, details and menu logic tested with a mocked repository (in `test_restaurant_search.py`, `test_restaurant_details.py` and `test_restaurant_menu.py`)
- **Repositories**
  - loading restaurants and handling invalid JSON (`test_restaurant_repository.py`)
  - saving restaurants: ID generation, persistence after restart, partial updates, write failures (`test_restaurant_repository_write.py`)
  - loading menus, orphaned items, invalid data, and a consistency check of the real data files (`test_menu_repository.py`)
  - saving menu items: global IDs, persistence, partial updates, ownership checks (`test_menu_repository_write.py`)
- **Web pages:** the customer and owner pages, static scripts, search controls, and the API calls the scripts make (`test_frontend.py`)

## Continuous Integration
GitHub Actions runs `python -m pytest -v` on every push and pull request, using Python 3.13 and `requirements.txt` ([.github/workflows/tests.yml](.github/workflows/tests.yml)). The result shows as a check on each pull request.

## Project Docs
- [docs/api-contract.md](docs/api-contract.md): M1 API contract (endpoints, models, status codes)
- [docs/decision-receipt.md](docs/decision-receipt.md): decision receipts for our main engineering decisions
- [docs/PROVENANCE.md](docs/PROVENANCE.md): provenance record for externally assisted work
- [scrum/](scrum/): team agreement and sprint notes