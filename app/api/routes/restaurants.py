from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.openapi import RESTAURANT_NOT_FOUND, RestaurantId, data_error
from app.core.config import settings
from app.repositories.menu_repository import MenuRepository
from app.repositories.restaurant_repository import (
    DataAccessError,
    RestaurantNotFoundError,
    RestaurantRepository,
)
from app.schemas.menu import MenuResponse
from app.schemas.restaurant import Restaurant, RestaurantCreate, RestaurantUpdate
from app.services.menu_service import MenuService
from app.services.restaurant_service import RestaurantService

router = APIRouter()


def get_restaurant_repository() -> RestaurantRepository:
    return RestaurantRepository(settings.data_dir / "restaurants.json")


def get_restaurant_service(
    repository: RestaurantRepository = Depends(get_restaurant_repository),
) -> RestaurantService:
    return RestaurantService(repository)


def get_menu_repository(
    restaurant_repository: RestaurantRepository = Depends(get_restaurant_repository),
) -> MenuRepository:
    return MenuRepository(settings.data_dir / "menus.json", restaurant_repository)


def get_menu_service(
    repository: MenuRepository = Depends(get_menu_repository),
) -> MenuService:
    return MenuService(repository)


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
    try:
        return service.search_restaurants(name=name, cuisine=cuisine)
    except DataAccessError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not load restaurant data: {exc}",
        ) from exc


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
    """Returns one restaurant by its ID. Returns `422` if `restaurant_id` is not an integer."""
    try:
        return service.get_restaurant(restaurant_id)
    except RestaurantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DataAccessError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not load restaurant data: {exc}",
        ) from exc


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
    """Returns the restaurant's menu items sorted by ID. Unavailable items are included with `is_available: false`.

    A restaurant with no items returns `200` with an empty `items` list. Returns `422` if `restaurant_id` is not an integer.
    """
    try:
        menu = service.get_menu(restaurant_id)
        return MenuResponse.model_validate(menu.model_dump())
    except RestaurantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DataAccessError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not load menu data: {exc}",
        ) from exc

@router.post(
    "/restaurants",
    response_model=Restaurant,
    status_code=201,
    summary="Create a restaurant",
    responses=data_error("Stored restaurant data could not be read or saved."),
)
def create_restaurant(
    new: RestaurantCreate,
    service: RestaurantService = Depends(get_restaurant_service),
) -> Restaurant:
    """Creates a restaurant and returns it with its new server-assigned `id`.

    Returns `422` if `name` or `cuisine` is missing or empty.
    """
    try:
        return service.create_restaurant(new)
    except DataAccessError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not save restaurant data: {exc}",
        ) from exc


@router.patch(
    "/restaurants/{restaurant_id}",
    response_model=Restaurant,
    status_code=200,
    summary="Update a restaurant",
    responses={
        **RESTAURANT_NOT_FOUND,
        **data_error("Stored restaurant data could not be read or saved."),
    },
)
def update_restaurant(
    restaurant_id: RestaurantId,
    changes: RestaurantUpdate,
    service: RestaurantService = Depends(get_restaurant_service),
) -> Restaurant:
    """Partially updates a restaurant. Only the fields sent are changed, and the `id` never changes.

    Returns `422` if `restaurant_id` is not an integer, or a field sent is empty or has the wrong type.
    """
    try:
        return service.update_restaurant(restaurant_id, changes)

    except RestaurantNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except DataAccessError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not update restaurant data: {exc}",
        ) from exc
