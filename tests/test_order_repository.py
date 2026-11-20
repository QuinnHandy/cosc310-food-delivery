"""OrderRepository (#93): storage only, tested without the API."""

import json

import pytest
from pydantic import ValidationError

from app.repositories.json_store import DataAccessError
from app.repositories.order_repository import OrderNotFoundError, OrderRepository
from app.schemas.order import Order, OrderDraft, OrderLine, OrderStatus


@pytest.fixture
def order_file(tmp_path):
    return tmp_path / "orders.json"


def make_draft(customer_id=4, restaurant_id=1, quantity=2, unit_price=15.5) -> OrderDraft:
    line_total = round(unit_price * quantity, 2)
    return OrderDraft(
        customer_id=customer_id,
        restaurant_id=restaurant_id,
        restaurant_name="Golden Dragon",
        items=[
            OrderLine(
                menu_item_id=1,
                name="Kung Pao Chicken",
                unit_price=unit_price,
                quantity=quantity,
                line_total=line_total,
            )
        ],
        subtotal=line_total,
        delivery_fee=4.99,
        total=round(line_total + 4.99, 2),
        delivery_address="123 Main St, Kelowna, BC",
    )


def test_missing_file_means_no_orders(order_file):
    repo = OrderRepository(order_file)
    assert repo.list_all() == []
    assert repo.list_for_customer(4) == []


def test_add_assigns_ids_status_and_time(order_file):
    repo = OrderRepository(order_file)
    first = repo.add(make_draft())
    second = repo.add(make_draft(customer_id=5))
    assert (first.id, second.id) == (1, 2)
    assert first.status == OrderStatus.placed
    assert first.created_at.tzinfo is not None


def test_order_survives_reload_with_its_snapshot(order_file):
    saved = OrderRepository(order_file).add(make_draft())
    loaded = OrderRepository(order_file).get_by_id(saved.id)
    assert loaded == saved
    assert loaded.items[0].name == "Kung Pao Chicken"
    assert loaded.items[0].unit_price == 15.5
    assert loaded.total == 35.99
    assert loaded.restaurant_name == "Golden Dragon"
    assert loaded.delivery_address == "123 Main St, Kelowna, BC"


def test_get_unknown_order_raises(order_file):
    repo = OrderRepository(order_file)
    repo.add(make_draft())
    with pytest.raises(OrderNotFoundError):
        repo.get_by_id(9)


def test_list_for_customer_returns_only_their_orders_newest_first(order_file):
    repo = OrderRepository(order_file)
    repo.add(make_draft(customer_id=4))
    repo.add(make_draft(customer_id=5))
    repo.add(make_draft(customer_id=4))
    assert [order.id for order in repo.list_for_customer(4)] == [3, 1]
    assert [order.id for order in repo.list_for_customer(5)] == [2]


def test_ids_are_not_reused(order_file):
    repo = OrderRepository(order_file)
    repo.add(make_draft())
    repo.add(make_draft())
    # Even if the newest order were removed from the file by hand, the next ID is max + 1,
    # and the order that remains keeps its ID.
    orders = json.loads(order_file.read_text())
    order_file.write_text(json.dumps(orders[:1]))
    assert OrderRepository(order_file).add(make_draft()).id == 2


def test_orders_are_not_changed_by_later_adds(order_file):
    repo = OrderRepository(order_file)
    first = repo.add(make_draft(unit_price=10.0))
    repo.add(make_draft(unit_price=99.0))
    assert repo.get_by_id(first.id).items[0].unit_price == 10.0


def test_draft_needs_at_least_one_line():
    with pytest.raises(ValidationError):
        OrderDraft(
            customer_id=4,
            restaurant_id=1,
            restaurant_name="Golden Dragon",
            items=[],
            subtotal=0,
            delivery_fee=0,
            total=0,
        )


@pytest.mark.parametrize("quantity", [0, -1])
def test_line_quantity_must_be_positive(quantity):
    with pytest.raises(ValidationError):
        OrderLine(menu_item_id=1, name="X", unit_price=1.0, quantity=quantity, line_total=0)


VALID_ORDER = {
    "id": 1, "customer_id": 4, "restaurant_id": 1, "restaurant_name": "Golden Dragon", "status": "placed",
    "items": [{"menu_item_id": 1, "name": "X", "unit_price": 1.0, "quantity": 1, "line_total": 1.0}],
    "subtotal": 1.0, "delivery_fee": 4.99, "total": 5.99,
    "delivery_address": "", "created_at": "2026-11-20T10:00:00Z",
}


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        json.dumps({"id": 1}),  # not a list
        json.dumps([{**VALID_ORDER, "items": []}]),  # no lines
        json.dumps([{**VALID_ORDER, "status": "teleported"}]),  # unknown status
        json.dumps([VALID_ORDER, VALID_ORDER]),  # duplicate IDs
    ],
)
def test_invalid_file_raises_data_access_error(order_file, content):
    order_file.write_text(content)
    with pytest.raises(DataAccessError):
        OrderRepository(order_file).list_all()


def test_valid_stored_order_loads(order_file):
    order_file.write_text(json.dumps([VALID_ORDER]))
    assert OrderRepository(order_file).get_by_id(1).customer_id == 4


def test_committed_orders_file_is_valid_and_starts_empty():
    # data/orders.json is committed as [] so the file exists from the first run.
    from app.core.config import PROJECT_ROOT

    assert OrderRepository(PROJECT_ROOT / "data" / "orders.json").list_all() == []
