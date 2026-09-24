from fastapi import APIRouter, Depends, HTTPException

from app.core.config import settings
from app.repositories.restaurant_repository import DataAccessError, RestaurantRepository
from app.schemas.restaurant import Restaurant
from app.services.restaurant_service import RestaurantService

router = APIRouter()


def get_restaurant_repository() -> RestaurantRepository:
    return RestaurantRepository(settings.data_dir / "restaurants.json")


def get_restaurant_service(
    repository: RestaurantRepository = Depends(get_restaurant_repository),
) -> RestaurantService:
    return RestaurantService(repository)


@router.get("/restaurants", response_model=list[Restaurant])
def list_restaurants(
    service: RestaurantService = Depends(get_restaurant_service),
) -> list[Restaurant]:
    try:
        return service.list_restaurants()
    except DataAccessError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not load restaurant data: {exc}",
        ) from exc
