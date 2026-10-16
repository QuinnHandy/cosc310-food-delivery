from fastapi import APIRouter, Depends, HTTPException, Query

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


@router.get("/restaurants", response_model=list[Restaurant])
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
    try:
        return service.search_restaurants(name=name, cuisine=cuisine)
    except DataAccessError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not load restaurant data: {exc}",
        ) from exc


@router.get("/restaurants/{restaurant_id}", response_model=Restaurant)
def get_restaurant(
    restaurant_id: int,
    service: RestaurantService = Depends(get_restaurant_service),
) -> Restaurant:
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
    responses={404: {"description": "Restaurant not found"}},
)
def get_restaurant_menu(
    restaurant_id: int,
    service: MenuService = Depends(get_menu_service),
) -> MenuResponse:
    """Returns the restaurant's menu items sorted by ID. A restaurant with no items returns an empty list."""
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

@router.post("/restaurants", response_model=Restaurant, status_code=201)
def create_restaurant(
    new: RestaurantCreate,
    service: RestaurantService = Depends(get_restaurant_service),
) -> Restaurant:
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
)
def update_restaurant(
    restaurant_id: int,
    changes: RestaurantUpdate,
    service: RestaurantService = Depends(get_restaurant_service),
) -> Restaurant:
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

