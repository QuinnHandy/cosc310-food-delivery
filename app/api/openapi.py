"""Shared OpenAPI definitions used by the route modules (documentation only)."""

from typing import Annotated

from fastapi import Path

from app.schemas.common import ErrorResponse

RestaurantId = Annotated[int, Path(description="ID of the restaurant.")]

RESTAURANT_NOT_FOUND = {
    404: {
        "model": ErrorResponse,
        "description": "No restaurant has this ID.",
        "content": {"application/json": {"example": {"detail": "Restaurant 99 not found"}}},
    }
}


def data_error(description: str) -> dict:
    """500 response for when the stored JSON data cannot be read or saved."""
    return {500: {"model": ErrorResponse, "description": description}}
