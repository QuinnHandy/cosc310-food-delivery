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

UNAUTHORIZED = {
    401: {
        "model": ErrorResponse,
        "description": "The email or password is wrong, or the bearer token is missing or not valid.",
        "content": {"application/json": {"example": {"detail": "Invalid email or password"}}},
    }
}

FORBIDDEN = {
    403: {
        "model": ErrorResponse,
        "description": "The account has been deactivated.",
        "content": {"application/json": {"example": {"detail": "This account has been deactivated"}}},
    }
}


NOT_SIGNED_IN = {
    401: {
        "model": ErrorResponse,
        "description": "No `Authorization: Bearer <token>` header, or the token is not a current session.",
        "content": {"application/json": {"example": {"detail": "Not authenticated"}}},
    }
}

NOT_ALLOWED = {
    403: {
        "model": ErrorResponse,
        "description": "The account is deactivated, or the signed-in user is not allowed to do this (wrong role, or not the owner of this restaurant).",
        "content": {
            "application/json": {"example": {"detail": "You do not have permission to do this"}}
        },
    }
}


def data_error(description: str) -> dict:
    """500 response for when the stored JSON data cannot be read or saved."""
    return {500: {"model": ErrorResponse, "description": description}}
