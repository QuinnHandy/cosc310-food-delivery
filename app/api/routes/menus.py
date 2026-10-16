
from fastapi import APIRouter, Depends, HTTPException

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
)
def add_menu_item(
    restaurant_id: int,
    new: MenuItemCreate,
    service: MenuService = Depends(get_menu_service),
) -> MenuItem:
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
