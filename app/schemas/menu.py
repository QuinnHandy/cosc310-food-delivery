from pydantic import BaseModel, Field


class MenuItemCreate(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""
    price: float = Field(gt=0)
    is_available: bool = True
    category: str = Field(min_length=1)
    image_url: str = ""


class MenuItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    description: str | None = None
    price: float | None = Field(default=None, gt=0)
    is_available: bool | None = None
    category: str | None = Field(default=None, min_length=1)
    image_url: str | None = None


class MenuItem(MenuItemCreate):
    id: int
    restaurant_id: int


class Menu(BaseModel):
    restaurant_id: int
    items: list[MenuItem]