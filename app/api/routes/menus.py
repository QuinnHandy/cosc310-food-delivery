
from fastapi import APIRouter, Depends

from app.api.dependencies import get_menu_service, require_restaurant_access
from app.api.openapi import (
    NOT_ALLOWED,
    NOT_SIGNED_IN,
    RESTAURANT_NOT_FOUND,
    RestaurantId,
    data_error,
)
from app.schemas.menu import MenuItem, MenuItemCreate
from app.services.menu_service import MenuService

router = APIRouter()


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
    """Add a menu item to a restaurant's menu."""
    return service.add_menu_item(restaurant_id, new)
