"""Tests for the shared pytest fixtures (#100)."""

import os

from app.core.config import PROJECT_ROOT
from app.repositories.session_repository import SessionRepository


COMMITTED_DATA = PROJECT_ROOT / "data"


def snapshot_committed_data():
    """Read the exact bytes of every committed JSON data file."""
    return {
        path.name: path.read_bytes()
        for path in COMMITTED_DATA.glob("*.json")
    }


def test_temp_data_dir_copies_seed_data(temp_data_dir):
    """Seed data is copied to a separate temporary directory."""
    assert temp_data_dir != COMMITTED_DATA
    assert os.environ["APP_DATA_DIR"] == str(temp_data_dir)

    for source in COMMITTED_DATA.glob("*.json"):
        if source.name == "sessions.json":
            continue  # Test sessions are generated separately.

        copied = temp_data_dir / source.name
        assert copied.exists()
        assert copied.read_bytes() == source.read_bytes()


def test_auth_headers_use_seeded_users(
    temp_data_dir,
    customer_headers,
    customer2_headers,
    owner_headers,
    owner2_headers,
    admin_headers,
    deactivated_customer_headers,
):
    """All test tokens correspond to the correct seeded users."""
    sessions = SessionRepository(temp_data_dir / "sessions.json")

    users = [
        (customer_headers, 4),
        (customer2_headers, 5),
        (owner_headers, 2),
        (owner2_headers, 3),
        (admin_headers, 1),
        (deactivated_customer_headers, 6),
    ]

    for headers, expected_id in users:
        token = headers["Authorization"].removeprefix("Bearer ")
        session = sessions.get(token)

        assert session is not None
        assert session.user_id == expected_id


def test_deactivated_customer_is_rejected(
    client, deactivated_customer_headers
):
    """A deactivated customer's token must not grant access."""
    response = client.get(
        "/cart", headers=deactivated_customer_headers
    )
    assert response.status_code == 403


def test_api_does_not_modify_committed_data(
    client, customer_headers, temp_data_dir
):
    """API writes affect only temporary JSON files."""
    before = snapshot_committed_data()

    response = client.post(
        "/cart/items",
        json={"menu_item_id": 1, "quantity": 2},
        headers=customer_headers,
    )

    assert response.status_code == 200
    assert (temp_data_dir / "carts.json").exists()

    after = snapshot_committed_data()

    # No original JSON file was added, removed or modified.
    assert after == before
