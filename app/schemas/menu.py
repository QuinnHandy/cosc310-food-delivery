from pydantic import BaseModel, Field


class MenuItemCreate(BaseModel):
    """Request body for adding a menu item. The ID and restaurant ID are set by the server."""

    name: str = Field(min_length=1, description="Item name. Must not be empty.")
    description: str = Field(default="", description="Short description of the item. Optional.")
    price: float = Field(gt=0, description="Price in dollars. Must be greater than 0.")
    is_available: bool = Field(
        default=True, description="Whether the item can currently be ordered."
    )
    category: str = Field(
        min_length=1, description="Menu section, e.g. 'Pizza' or 'Starters'. Must not be empty."
    )
    image_url: str = Field(default="", description="Link to an image of the item. Optional.")


class MenuItemUpdate(BaseModel):
    """Partial update for a menu item. Leave a field out to keep its current value."""

    name: str | None = Field(
        default=None, min_length=1, description="New item name. Must not be empty if sent."
    )
    description: str | None = Field(default=None, description="New description.")
    price: float | None = Field(
        default=None, gt=0, description="New price in dollars. Must be greater than 0 if sent."
    )
    is_available: bool | None = Field(
        default=None, description="Whether the item can currently be ordered."
    )
    category: str | None = Field(
        default=None, min_length=1, description="New menu section. Must not be empty if sent."
    )
    image_url: str | None = Field(default=None, description="New image link.")


class MenuItem(MenuItemCreate):
    """A menu item as stored and returned by the API."""

    id: int = Field(description="Server-assigned unique ID across all menu items. Never changes.")
    restaurant_id: int = Field(description="ID of the restaurant this item belongs to.")


class Menu(BaseModel):
    """A restaurant's menu as returned by the repository."""

    restaurant_id: int = Field(description="ID of the restaurant this menu belongs to.")
    items: list[MenuItem] = Field(description="The restaurant's menu items sorted by ID.")


class MenuItemResponse(MenuItem):
    """A menu item as returned by the API."""


class MenuResponse(BaseModel):
    """A restaurant's menu as returned by GET /restaurants/{restaurant_id}/menu."""

    restaurant_id: int = Field(description="ID of the restaurant this menu belongs to.")
    items: list[MenuItemResponse] = Field(
        description="The restaurant's menu items sorted by ID. Empty if it has no items."
    )
