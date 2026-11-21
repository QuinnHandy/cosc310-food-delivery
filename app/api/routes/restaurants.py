from fastapi import APIRouter, Depends, Query

from app.api.dependencies import (
    get_menu_service,
    get_restaurant_service,
    require_restaurant_access,
    require_role,
)
from app.api.openapi import (
    NOT_ALLOWED,
    NOT_SIGNED_IN,
    RESTAURANT_NOT_FOUND,
    RestaurantId,
    data_error,
)
from app.schemas.menu import MenuResponse
from app.schemas.restaurant import Restaurant, RestaurantCreate, RestaurantUpdate
from app.services.menu_service import MenuService
from app.services.restaurant_service import RestaurantService

router = APIRouter()


@router.get(
    "/restaurants",
    response_model=list[Restaurant],
    summary="List, search, and filter restaurants",
    responses=data_error("Stored restaurant data could not be read."),
)
def list_restaurants(
    name: str | None = Query(
        None,
        description="Partial match on restaurant name, ignoring case (e.g. 'piz' finds 'Pizza Place').",
    ),
    cuisine: str | None = Query(
        None,
        description="Exact match on cuisine, ignoring case (e.g. 'italian').",
    ),
    service: RestaurantService = Depends(get_restaurant_service),
) -> list[Restaurant]:
    """Returns all restaurants sorted by ID. The optional `name` and `cuisine` filters narrow the results; if both are given, a restaurant must match both.

    Spaces around a value are trimmed, and an empty or spaces-only value is ignored. If nothing matches, the response is `200` with an empty list, not a `404`.
    """
    return service.search_restaurants(name=name, cuisine=cuisine)


@router.get(
    "/restaurants/{restaurant_id}",
    response_model=Restaurant,
    summary="Get restaurant details",
    responses={
        **RESTAURANT_NOT_FOUND,
        **data_error("Stored restaurant data could not be read."),
    },
)
def get_restaurant(
    restaurant_id: RestaurantId,
    service: RestaurantService = Depends(get_restaurant_service),
) -> Restaurant:
    """Returns a restaurant by its ID."""
    return service.get_restaurant(restaurant_id)



@router.get(
    "/restaurants/{restaurant_id}/menu",
    response_model=MenuResponse,
    summary="View a restaurant's menu",
    responses={
        **RESTAURANT_NOT_FOUND,
        **data_error("Stored restaurant or menu data could not be read."),
    },
)

def get_restaurant_menu(
    restaurant_id: RestaurantId,
    service: MenuService = Depends(get_menu_service),
) -> MenuResponse:
    """Returns the restaurant's menu items sorted by ID."""
    menu = service.get_menu(restaurant_id)
    return MenuResponse.model_validate(menu.model_dump())


@router.post(
    "/restaurants",
    response_model=Restaurant,
    status_code=201,
    summary="Create a restaurant",
    dependencies=[Depends(require_role("restaurant_owner", "admin"))],
    responses={
        **NOT_SIGNED_IN,
        **NOT_ALLOWED,
        **data_error("Stored restaurant data could not be read or saved."),
    },
)
def create_restaurant(
    new: RestaurantCreate,
    service: RestaurantService = Depends(get_restaurant_service),
) -> Restaurant:
    """Creates a restaurant and returns it with its new server-assigned `id`. Requires a signed-in `restaurant_owner` or `admin`.

    Returns `401` if there is no valid bearer token, `403` for any other role or a deactivated account, and `422` if `name` or `cuisine` is missing or empty.
    """
    return service.create_restaurant(new)


@router.patch(
    "/restaurants/{restaurant_id}",
    response_model=Restaurant,
    status_code=200,
    summary="Update a restaurant",
    dependencies=[Depends(require_restaurant_access)],
    responses={
        **NOT_SIGNED_IN,
        **NOT_ALLOWED,
        **RESTAURANT_NOT_FOUND,
        **data_error("Stored restaurant data could not be read or saved."),
    },
)
def update_restaurant(
    restaurant_id: RestaurantId,
    changes: RestaurantUpdate,
    service: RestaurantService = Depends(get_restaurant_service),
) -> Restaurant:
    """Partially updates a restaurant. Only the fields sent are changed, and the `id` never changes. Requires an `admin` or the `restaurant_owner` of this restaurant.

    Returns `401` if there is no valid bearer token and `403` for any other user or a deactivated account. A non-admin gets `403` rather than `404` for an ID that does not exist. Returns `422` if `restaurant_id` is not an integer, or a field sent is empty or has the wrong type.
    """
    return service.update_restaurant(restaurant_id, changes)
