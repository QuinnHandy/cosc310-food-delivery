"""Shared pytest fixtures for integration and API tests (#100).

Uses the existing app_data fixture to keep all JSON writes
inside a temporary directory rather than committed data/.
"""

import pytest
from app_data_helpers import app_data  # noqa: F401


@pytest.fixture
def temp_data_dir(app_data):
    """Return the isolated directory containing copied JSON data."""
    return app_data.data_dir


@pytest.fixture
def client(app_data):
    """Return a FastAPI TestClient connected to temporary data."""
    return app_data.client


@pytest.fixture
def customer_headers(app_data):
    """Authorization headers for Alice, an active customer."""
    return app_data.headers["customer"]


@pytest.fixture
def customer2_headers(app_data):
    """Authorization headers for Bob, another active customer."""
    return app_data.headers["customer2"]


@pytest.fixture
def owner_headers(app_data):
    """Authorization headers for the owner of restaurant 1."""
    return app_data.headers["owner1"]


@pytest.fixture
def owner2_headers(app_data):
    """Authorization headers for the owner of restaurant 2."""
    return app_data.headers["owner2"]


@pytest.fixture
def admin_headers(app_data):
    """Authorization headers for the administrator."""
    return app_data.headers["admin"]


@pytest.fixture
def deactivated_customer_headers(app_data):
    """Session headers for Carol, a deactivated customer."""
    return app_data.headers["deactivated"]
