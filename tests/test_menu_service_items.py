"""MenuService (#38, #87) on a temporary copy of the seed data, without HTTP."""

import shutil

import pytest

from app.core.config import PROJECT_ROOT
from app.repositories.menu_repository import MenuItemNotFoundError, MenuRepository
from app.repositories.restaurant_repository import RestaurantNotFoundError, RestaurantRepository
from app.schemas.menu import MenuItemUpdate
from app.services.menu_service import MenuService


@pytest.fixture
def service(tmp_path):
    for name in ("restaurants.json", "menus.json"):
        shutil.copy(PROJECT_ROOT / "data" / name, tmp_path / name)
    restaurants = RestaurantRepository(tmp_path / "restaurants.json")
    repo = MenuRepository(tmp_path / "menus.json", restaurants)
    return MenuService(repo), repo


def test_customer_menu_hides_deactivated_but_keeps_unavailable_items(service):
    svc, repo = service
    svc.deactivate_menu_item(1, 1)
    ids = [item.id for item in svc.get_menu(1).items]
    assert ids == [2, 3]  # item 3 is unavailable but still listed
    assert [item.id for item in repo.get_menu(1).items] == [1, 2, 3]  # still stored


def test_deactivate_keeps_the_item_and_its_details(service):
    svc, repo = service
    svc.deactivate_menu_item(1, 1)
    item = repo.get_item(1)
    assert item.is_active is False and item.name == "Kung Pao Chicken" and item.price == 15.5


def test_deactivate_twice_is_not_an_error(service):
    svc, repo = service
    svc.deactivate_menu_item(1, 1)
    svc.deactivate_menu_item(1, 1)
    assert repo.get_item(1).is_active is False


def test_update_toggles_availability_and_cannot_change_is_active(service):
    svc, repo = service
    assert svc.update_menu_item(1, 1, MenuItemUpdate(is_available=False)).is_available is False
    assert svc.update_menu_item(1, 1, MenuItemUpdate(is_available=True)).is_available is True
    assert not hasattr(MenuItemUpdate(), "is_active")
    assert repo.get_item(1).is_active is True


@pytest.mark.parametrize("restaurant_id, item_id, error", [
    (1, 999, MenuItemNotFoundError),
    (1, 4, MenuItemNotFoundError),  # item 4 belongs to restaurant 2
    (99, 1, RestaurantNotFoundError),
])
def test_unknown_item_or_restaurant_raises(service, restaurant_id, item_id, error):
    svc, _ = service
    with pytest.raises(error):
        svc.deactivate_menu_item(restaurant_id, item_id)
    with pytest.raises(error):
        svc.update_menu_item(restaurant_id, item_id, MenuItemUpdate(price=5))
