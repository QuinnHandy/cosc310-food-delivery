"""Tests for centralized domain error handling (Issue #107)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import (
    DomainError,
    UnauthorizedError,
    ForbiddenError,
    NotFoundError,
    ConflictError,
    BusinessRuleError,
    DataAccessError,
)
from app.main import app, domain_error_handler
from app.services.checkout_service import (
    CheckoutNotAllowedError,
    DeliveryAddressRequiredError,
    InvalidQuantityError,
)


@pytest.mark.parametrize(
    "error, status, code, detail",
    [
        (UnauthorizedError("Invalid token"), 401, "unauthorized", "Invalid token"),
        (ForbiddenError("Access denied"), 403, "forbidden", "Access denied"),
        (NotFoundError("Not found"), 404, "not_found", "Not found"),
        (ConflictError("Already exists"), 409, "conflict", "Already exists"),
        (BusinessRuleError("Invalid quantity"), 422, "business_rule", "Invalid quantity"),
        (
            DataAccessError("Secret database information"),
            500,
            "data_access_error",
            "Could not access application data",
        ),
    ],
)
def test_domain_error_mapping(error, status, code, detail):
    test_app = FastAPI()
    test_app.add_exception_handler(DomainError, domain_error_handler)

    @test_app.get("/test-error")
    def trigger_error():
        raise error

    response = TestClient(test_app).get("/test-error")

    assert response.status_code == status
    assert response.json() == {
        "detail": detail,
        "code": code,
    }

    if status == 401:
        assert response.headers["WWW-Authenticate"] == "Bearer"
    else:
        assert "WWW-Authenticate" not in response.headers


def test_main_app_registers_domain_handler():
    assert app.exception_handlers[DomainError] is domain_error_handler


@pytest.mark.parametrize(
    "error, status, code",
    [
        (CheckoutNotAllowedError("Not allowed"), 403, "forbidden"),
        (DeliveryAddressRequiredError("Address required"), 422, "business_rule"),
        (InvalidQuantityError("Invalid quantity"), 422, "business_rule"),
    ],
)
def test_checkout_error_inheritance(error, status, code):
    test_app = FastAPI()
    test_app.add_exception_handler(DomainError, domain_error_handler)

    @test_app.get("/test-error")
    def trigger_error():
        raise error

    response = TestClient(test_app).get("/test-error")

    assert response.status_code == status
    assert response.json() == {
        "detail": str(error),
        "code": code,
    }
