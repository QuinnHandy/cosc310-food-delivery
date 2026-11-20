
from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import require_restaurant_access
from app.api.openapi import (
    NOT_ALLOWED,
    NOT_SIGNED_IN,
    RESTAURANT_NOT_FOUND,
    RestaurantId,
    data_error,
)
from app.core.config import settings
from app.repositories.menu_repository import MenuRepository
from app.repositories.restaurant_repository import (
    DataAccessError,
    RestaurantNotFoundError,
    RestaurantRepository,
)
from app.schemas.menu import MenuItem, MenuItemCreate
from app.services.menu_service import MenuService

router = APIRouter()


def get_menu_repository() -> MenuRepository:
    restaurant_repository = RestaurantRepository(
        settings.data_dir / "restaurants.json"
    )
    return MenuRepository(
        settings.data_dir / "menus.json",
        restaurant_repository,
    )


def get_menu_service(
    repository: MenuRepository = Depends(get_menu_repository),
) -> MenuService:
    return MenuService(repository)


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
    try:
        return service.add_menu_item(restaurant_id, new)

    except RestaurantNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except DataAccessError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not save menu item: {exc}",
        ) from exc
