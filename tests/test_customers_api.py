"""Customer account endpoints (#83-#86), against a temporary copy of the seed data."""

from fastapi.testclient import TestClient

from app.main import app
from auth_helpers import auth  # noqa: F401  (pytest fixture)

client = TestClient(app)
PASSWORD = "Password123!"  # every seeded user's password


def register(**overrides):
    body = {"name": "Dana", "email": "dana@example.com", "password": "longenough", **overrides}
    return client.post("/customers", json=body)


# ---- POST /customers (#83) ----

def test_register_returns_201_without_password(auth):
    response = register(delivery_address="1 Lake Rd")
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "dana@example.com"
    assert body["delivery_address"] == "1 Lake Rd"
    assert body["is_active"] is True
    assert "password" not in body and "password_hash" not in body


def test_registered_customer_can_sign_in_and_view_profile(auth):
    customer_id = register().json()["id"]
    login = client.post("/auth/login", json={"email": "DANA@example.com", "password": "longenough"})
    assert login.status_code == 200
    assert login.json()["role"] == "customer"
    me = client.get("/customers/me", headers={"Authorization": f"Bearer {login.json()['token']}"})
    assert me.json()["id"] == customer_id


def test_register_with_used_email_returns_409(auth):
    response = register(email="alice@foodapp.test")
    assert response.status_code == 409
    assert response.json()["detail"] == "An account with this email already exists"


def test_register_cannot_choose_role(auth):
    assert register(role="admin").status_code == 422


def test_register_invalid_fields_return_422(auth):
    assert register(password="short").status_code == 422
    assert register(name="").status_code == 422
    assert register(email="nope").status_code == 422


# ---- GET /customers/me and /customers/{id} (#84) ----

def test_get_my_profile(auth):
    response = client.get("/customers/me", headers=auth["customer"])
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "id": 4,
        "email": "alice@foodapp.test",
        "name": "Alice Smith",
        "phone": "250-555-0101",
        "delivery_address": "123 Main St, Kelowna, BC",
        "is_active": True,
    }


def test_profile_needs_a_customer_token(auth):
    assert client.get("/customers/me").status_code == 401
    assert client.get("/customers/me", headers=auth["owner1"]).status_code == 403
    assert client.get("/customers/me", headers=auth["deactivated"]).status_code == 403


def test_admin_can_view_any_customer(auth):
    response = client.get("/customers/5", headers=auth["admin"])
    assert response.status_code == 200
    assert response.json()["name"] == "Bob Jones"


def test_admin_view_unknown_or_non_customer_returns_404(auth):
    assert client.get("/customers/999", headers=auth["admin"]).status_code == 404
    assert client.get("/customers/2", headers=auth["admin"]).status_code == 404  # an owner


def test_customer_cannot_view_other_customers(auth):
    assert client.get("/customers/5", headers=auth["customer"]).status_code == 403


# ---- PATCH /customers/me (#85) ----

def test_update_address_is_saved(auth):
    response = client.patch(
        "/customers/me", json={"delivery_address": "77 New St"}, headers=auth["customer"]
    )
    assert response.status_code == 200
    assert response.json()["delivery_address"] == "77 New St"
    assert response.json()["name"] == "Alice Smith"
    again = client.get("/customers/me", headers=auth["customer"])
    assert again.json()["delivery_address"] == "77 New St"


def test_update_rejects_empty_and_protected_fields(auth):
    for body in ({"name": ""}, {"delivery_address": ""}, {"email": "a@b.co"}, {"role": "admin"}, {"is_active": False}):
        response = client.patch("/customers/me", json=body, headers=auth["customer"])
        assert response.status_code == 422, body


def test_update_needs_an_active_customer(auth):
    assert client.patch("/customers/me", json={"phone": "1"}).status_code == 401
    assert client.patch("/customers/me", json={"phone": "1"}, headers=auth["deactivated"]).status_code == 403


# ---- deactivate (#86) ----

def test_deactivate_me_then_token_and_sign_in_are_refused(auth):
    response = client.post("/customers/me/deactivate", headers=auth["customer"])
    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert client.get("/customers/me", headers=auth["customer"]).status_code == 403
    login = client.post("/auth/login", json={"email": "alice@foodapp.test", "password": PASSWORD})
    assert login.status_code == 403
    # still on record for the admin, not deleted
    kept = client.get("/customers/4", headers=auth["admin"])
    assert kept.status_code == 200 and kept.json()["is_active"] is False


def test_admin_deactivates_customer_and_twice_returns_409(auth):
    first = client.post("/customers/5/deactivate", headers=auth["admin"])
    assert first.status_code == 200
    assert client.post("/customers/5/deactivate", headers=auth["admin"]).status_code == 409


def test_admin_deactivate_unknown_returns_404_and_others_403(auth):
    assert client.post("/customers/999/deactivate", headers=auth["admin"]).status_code == 404
    assert client.post("/customers/5/deactivate", headers=auth["customer"]).status_code == 403
    assert client.post("/customers/5/deactivate").status_code == 401


def test_customer_endpoints_are_documented():
    paths = client.get("/openapi.json").json()["paths"]
    assert {"401", "403", "422"} <= paths["/customers/me"]["patch"]["responses"].keys()
    assert "409" in paths["/customers"]["post"]["responses"]
    assert {"404", "409"} <= paths["/customers/{customer_id}/deactivate"]["post"]["responses"].keys()
