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
## API Endpoints
| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check, returns 200 |
| GET | `/restaurants` | Lists all restaurants |

Interactive API docs: http://127.0.0.1:8000/docs

## Running Tests
Run the full test suite from the repository root:
```python -m pytest -v```

The test suite covers:
- the /health endpoint
- the /restaurants endpoint
- invalid endpoint handling
- restaurant repository behavior using temporary JSON data
- repository error handling for invalid JSON

## Data
Sample restaurant data is stored in `data/restaurants.json`.
The data location can be changed with the `APP_DATA_DIR` environment variable. Tests use this to run against temporary data.

## Repository Structure
```
app/
  api/routes/      # FastAPI routes (HTTP layer)
  services/        # Business logic
  repositories/    # Data access (reads JSON)
  schemas/         # Pydantic models
  core/            # Configuration
  main.py          # App entry point
data/              # Sample JSON data
tests/             # pytest test suite
scrum/             # Team agreement
```
