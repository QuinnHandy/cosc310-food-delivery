import pytest

from app.main import app

SCHEMA = app.openapi()
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}

OPERATIONS = [
    (method.upper(), path, operation)
    for path, item in SCHEMA["paths"].items()
    for method, operation in item.items()
    if method in HTTP_METHODS
]

# Every route that looks up a restaurant by ID and can therefore return 404.
RESTAURANT_ID_ROUTES = [
    ("get", "/restaurants/{restaurant_id}"),
    ("patch", "/restaurants/{restaurant_id}"),
    ("get", "/restaurants/{restaurant_id}/menu"),
    ("post", "/restaurants/{restaurant_id}/menu"),
]


def operation_id(param):
    return f"{param[0]} {param[1]}" if isinstance(param, tuple) else None


def test_all_m1_endpoints_are_documented():
    documented = {(method, path) for method, path, _ in OPERATIONS}
    assert documented == {
        ("GET", "/health"),
        ("GET", "/restaurants"),
        ("POST", "/restaurants"),
        ("GET", "/restaurants/{restaurant_id}"),
        ("PATCH", "/restaurants/{restaurant_id}"),
        ("GET", "/restaurants/{restaurant_id}/menu"),
        ("POST", "/restaurants/{restaurant_id}/menu"),
    }


# The web pages are not API endpoints, so they are hidden from /docs.
@pytest.mark.parametrize("path", ["/", "/owner"])
def test_frontend_pages_are_hidden_from_docs(path):
    assert path not in SCHEMA["paths"]


@pytest.mark.parametrize("method, path, operation", OPERATIONS, ids=[f"{m} {p}" for m, p, _ in OPERATIONS])
def test_every_operation_has_summary_and_description(method, path, operation):
    assert operation.get("summary", "").strip()
    assert operation.get("description", "").strip()


@pytest.mark.parametrize("method, path, operation", OPERATIONS, ids=[f"{m} {p}" for m, p, _ in OPERATIONS])
def test_every_operation_documents_a_success_response_model(method, path, operation):
    success = next(code for code in operation["responses"] if code.startswith("2"))
    assert "schema" in operation["responses"][success]["content"]["application/json"]


@pytest.mark.parametrize("method, path, operation", OPERATIONS, ids=[f"{m} {p}" for m, p, _ in OPERATIONS])
def test_every_parameter_has_a_description(method, path, operation):
    for parameter in operation.get("parameters", []):
        assert parameter.get("description", "").strip(), parameter["name"]


@pytest.mark.parametrize("method, path", RESTAURANT_ID_ROUTES, ids=operation_id)
def test_restaurant_id_routes_document_404(method, path):
    not_found = SCHEMA["paths"][path][method]["responses"]["404"]
    assert not_found["description"]
    assert not_found["content"]["application/json"]["schema"] == {"$ref": "#/components/schemas/ErrorResponse"}


@pytest.mark.parametrize("method, path", RESTAURANT_ID_ROUTES, ids=operation_id)
def test_restaurant_id_routes_document_422(method, path):
    assert "422" in SCHEMA["paths"][path][method]["responses"]


@pytest.mark.parametrize("method, path, operation", OPERATIONS, ids=[f"{m} {p}" for m, p, _ in OPERATIONS])
def test_data_routes_document_500(method, path, operation):
    if path == "/health":
        assert "500" not in operation["responses"]
    else:
        assert operation["responses"]["500"]["description"]


def test_health_documents_no_error_responses():
    responses = SCHEMA["paths"]["/health"]["get"]["responses"]
    assert set(responses) == {"200"}


def test_create_routes_document_201():
    assert "201" in SCHEMA["paths"]["/restaurants"]["post"]["responses"]
    assert "201" in SCHEMA["paths"]["/restaurants/{restaurant_id}/menu"]["post"]["responses"]


# Every field of the request and response models should explain itself in /docs.
@pytest.mark.parametrize("name", [
    "Restaurant", "RestaurantCreate", "RestaurantUpdate",
    "MenuItem", "MenuItemCreate", "MenuResponse", "MenuItemResponse",
    "ErrorResponse", "HealthResponse",
])
def test_schema_fields_have_descriptions(name):
    for field, spec in SCHEMA["components"]["schemas"][name]["properties"].items():
        assert spec.get("description", "").strip(), f"{name}.{field}"
