
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Response

from app.api.dependencies import get_menu_service, require_restaurant_access
from app.api.openapi import (
    NOT_ALLOWED,
    NOT_SIGNED_IN,
    RESTAURANT_NOT_FOUND,
    RestaurantId,
    data_error,
)
from app.schemas.common import ErrorResponse
from app.schemas.menu import MenuItem, MenuItemCreate, MenuItemUpdate
from app.services.menu_service import MenuService

router = APIRouter()

ItemId = Annotated[int, Path(description="ID of the menu item.")]

ITEM_NOT_FOUND = {
    404: {
        "model": ErrorResponse,
        "description": "No restaurant has this ID, or this restaurant has no menu item with this ID.",
        "content": {
            "application/json": {
                "example": {
                    "detail": "Menu item 99 not found for restaurant 1",
                    "code": "not_found",
                }
            }
        },
    }
}


@router.post(
    "/restaurants/{restaurant_id}/menu",
    response_model=MenuItem,
    status_code=201,
    summary="Add a menu item",
    dependencies=[Depends(require_restaurant_access)],
    responses={
        **NOT_SIGNED_IN,
        **NOT_ALLOWED,
        **RESTAURANT_NOT_FOUND,
        **data_error("Stored restaurant or menu data could not be read or saved."),
    },
)
def add_menu_item(
    restaurant_id: RestaurantId,
    new: MenuItemCreate,
    service: MenuService = Depends(get_menu_service),
) -> MenuItem:
    """Adds an item to the restaurant's menu and returns it with its new server-assigned `id` and `restaurant_id`. Requires an `admin` or the `restaurant_owner` of this restaurant.

    Returns `401` if there is no valid bearer token and `403` for any other user or a deactivated account. A non-admin gets `403` rather than `404` for an ID that does not exist. Returns `422` if `restaurant_id` is not an integer, `name`, `price`, or `category` is missing, a text field that must not be empty is empty, or `price` is not greater than 0.
    """
    return service.add_menu_item(restaurant_id, new)


@router.patch(
    "/restaurants/{restaurant_id}/menu/items/{item_id}",
    response_model=MenuItem,
    summary="Update a menu item",
    dependencies=[Depends(require_restaurant_access)],
    responses={
        **NOT_SIGNED_IN,
        **NOT_ALLOWED,
        **ITEM_NOT_FOUND,
        **data_error("Stored restaurant or menu data could not be read or saved."),
    },
)
def update_menu_item(
    restaurant_id: RestaurantId,
    item_id: ItemId,
    changes: MenuItemUpdate,
    service: MenuService = Depends(get_menu_service),
) -> MenuItem:
    """Changes only the fields sent and returns the updated item. Requires an `admin` or the `restaurant_owner` of this restaurant.

    Send `{"is_available": false}` to make an item temporarily unavailable (customers still see it, marked unavailable) and `{"is_available": true}` to make it available again. Deactivating an item is a separate request (`DELETE`), so `is_active` cannot be changed here and is ignored if sent.

    Returns `401` without a valid token and `403` for any other user or a deactivated account (a non-admin gets `403` rather than `404` for a restaurant that does not exist). Returns `404` for an unknown restaurant or item, or an item that belongs to a different restaurant, and `422` if a field has the wrong type or `price` is not greater than 0.
    """
    return service.update_menu_item(restaurant_id, item_id, changes)


@router.delete(
    "/restaurants/{restaurant_id}/menu/items/{item_id}",
    status_code=204,
    summary="Deactivate a menu item",
    dependencies=[Depends(require_restaurant_access)],
    responses={
        **NOT_SIGNED_IN,
        **NOT_ALLOWED,
        **ITEM_NOT_FOUND,
        **data_error("Stored restaurant or menu data could not be read or saved."),
    },
)
def deactivate_menu_item(
    restaurant_id: RestaurantId,
    item_id: ItemId,
    service: MenuService = Depends(get_menu_service),
) -> Response:
    """Deactivates a menu item (a soft delete) and returns `204` with no body. Requires an `admin` or the `restaurant_owner` of this restaurant.

    The item is **never removed** from the stored menu, because past orders and carts refer to its ID. It is hidden from the customer menu (`GET /restaurants/{restaurant_id}/menu`) and customers can no longer add it to a cart. Deactivating an item that is already deactivated also returns `204`.

    Returns `401` without a valid token and `403` for any other user or a deactivated account (a non-admin gets `403` rather than `404` for a restaurant that does not exist). Returns `404` for an unknown restaurant or item, or an item that belongs to a different restaurant.
    """
    service.deactivate_menu_item(restaurant_id, item_id)
    return Response(status_code=204)
