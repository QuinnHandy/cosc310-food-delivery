"""OrderService (#96): who sees which orders, tested without the API."""

import shutil

import pytest

from app.core.config import PROJECT_ROOT
from app.repositories.order_repository import OrderNotFoundError, OrderRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.repositories.user_repository import UserRepository
from app.schemas.order import OrderDraft, OrderLine
from app.services.customer_service import CustomerNotFoundError, CustomerService
from app.services.order_service import OrderNotAllowedError, OrderService


def make_draft(customer_id=4, unit_price=15.5, quantity=2) -> OrderDraft:
    line_total = round(unit_price * quantity, 2)
    return OrderDraft(
        customer_id=customer_id,
        restaurant_id=1,
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


@pytest.fixture
def parts(tmp_path):
    for name in ("restaurants.json", "users.json"):
        shutil.copy(PROJECT_ROOT / "data" / name, tmp_path / name)
    restaurants = RestaurantRepository(tmp_path / "restaurants.json")
    users = UserRepository(tmp_path / "users.json", restaurants)
    orders = OrderRepository(tmp_path / "orders.json")
    return OrderService(orders, CustomerService(users)), orders, users


def test_my_orders_are_newest_first(parts):
    service, orders, users = parts
    first, second, third = (orders.add(make_draft()) for _ in range(3))
    assert [o.id for o in service.list_my_orders(users.get(4))] == [third.id, second.id, first.id]


def test_my_orders_leave_out_other_customers(parts):
    service, orders, users = parts
    mine = orders.add(make_draft(customer_id=4))
    orders.add(make_draft(customer_id=5))
    assert [o.id for o in service.list_my_orders(users.get(4))] == [mine.id]


def test_no_orders_is_an_empty_list_not_an_error(parts):
    service, _, users = parts
    assert service.list_my_orders(users.get(4)) == []
    assert service.list_orders_for_customer(4) == []


def test_admin_lookup_returns_that_customers_orders(parts):
    service, orders, _ = parts
    orders.add(make_draft(customer_id=4))
    bobs = orders.add(make_draft(customer_id=5))
    assert [o.id for o in service.list_orders_for_customer(5)] == [bobs.id]


@pytest.mark.parametrize("customer_id", [99, 1, 2])  # unknown, admin, restaurant owner
def test_admin_lookup_of_a_non_customer_raises_not_found(parts, customer_id):
    service, _, _ = parts
    with pytest.raises(CustomerNotFoundError):
        service.list_orders_for_customer(customer_id)


# ---- get_order (#95) ----


def test_customer_gets_their_own_order_with_its_snapshot(parts):
    service, orders, users = parts
    placed = orders.add(make_draft(customer_id=4))
    order = service.get_order(users.get(4), placed.id)
    assert order == placed
    assert order.items[0].name == "Kung Pao Chicken"


def test_customer_asking_for_another_customers_order_is_not_allowed(parts):
    service, orders, users = parts
    bobs = orders.add(make_draft(customer_id=5))
    with pytest.raises(OrderNotAllowedError):
        service.get_order(users.get(4), bobs.id)


def test_admin_can_get_any_order(parts):
    service, orders, users = parts
    alices = orders.add(make_draft(customer_id=4))
    bobs = orders.add(make_draft(customer_id=5))
    assert service.get_order(users.get(1), alices.id) == alices
    assert service.get_order(users.get(1), bobs.id) == bobs


def test_get_order_with_an_unknown_id_raises_not_found(parts):
    service, _, users = parts
    with pytest.raises(OrderNotFoundError):
        service.get_order(users.get(4), 99)
    with pytest.raises(OrderNotFoundError):
        service.get_order(users.get(1), 99)
