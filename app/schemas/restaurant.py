from pydantic import BaseModel, Field


class Restaurant(BaseModel):
    """A restaurant as stored and returned by the API."""

    id: int = Field(description="Server-assigned unique ID. Never changes.")
    name: str = Field(description="Restaurant name.")
    cuisine: str = Field(description="Type of food served, e.g. 'Italian'.")


class RestaurantCreate(BaseModel):
    """Request body for creating a restaurant. The ID is assigned by the server."""

    name: str = Field(min_length=1, description="Restaurant name. Must not be empty.")
    cuisine: str = Field(
        min_length=1, description="Type of food served, e.g. 'Italian'. Must not be empty."
    )


class RestaurantUpdate(BaseModel):
    """Request body for a partial update. Leave a field out to keep its current value."""

    name: str | None = Field(
        default=None, min_length=1, description="New restaurant name. Must not be empty if sent."
    )
    cuisine: str | None = Field(
        default=None, min_length=1, description="New cuisine. Must not be empty if sent."
    )
