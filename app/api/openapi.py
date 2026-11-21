"""Shared OpenAPI definitions used by the route modules (documentation only)."""

from typing import Annotated

from fastapi import Path

from app.schemas.common import ErrorResponse

RestaurantId = Annotated[int, Path(description="ID of the restaurant.")]


RESTAURANT_NOT_FOUND = {
    404: {
        "model": ErrorResponse,
        "description": "No restaurant has this ID.",
        "content": {
            "application/json": {
                "example": {
                    "detail": "Restaurant 99 not found",
                    "code": "not_found",
                }
            }
        },
    }
}

UNAUTHORIZED = {
    401: {
        "model": ErrorResponse,
        "description": "The email or password is wrong, or the bearer token is missing or invalid.",
        "content": {
            "application/json": {
                "example": {
                    "detail": "Invalid email or password",
                    "code": "unauthorized",
                }
            }
        },
    }
}

FORBIDDEN = {
    403: {
        "model": ErrorResponse,
        "description": "The account has been deactivated.",
        "content": {
            "application/json": {
                "example": {
                    "detail": "This account has been deactivated",
                    "code": "forbidden",
                }
            }
        },
    }
}

NOT_SIGNED_IN = {
    401: {
        "model": ErrorResponse,
        "description": "Missing or invalid bearer token.",
        "content": {
            "application/json": {
                "example": {
                    "detail": "Not authenticated",
                    "code": "unauthorized",
                }
            }
        },
    }
}

NOT_ALLOWED = {
    403: {
        "model": ErrorResponse,
        "description": "The account is deactivated or the user lacks permission.",
        "content": {
            "application/json": {
                "example": {
                    "detail": "You do not have permission to do this",
                    "code": "forbidden",
                }
            }
        },
    }
}


def data_error(description: str) -> dict:
    """500 response for stored data that cannot be read or saved."""
    return {
        500: {
            "model": ErrorResponse,
            "description": description,
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Could not access application data",
                        "code": "data_access_error",
                    }
                }
            },
        }
    }
